export type AdviceAction = "silent" | "say" | "ask" | "watch";
export type AdvicePriority = "normal" | "high";

export interface Advice {
	action: AdviceAction;
	text: string;
	priority: AdvicePriority;
	reason: string;
	recordingId: string;
	revision: number;
	shownAt: number;
	manual: boolean;
}

export interface Recording {
	id: string;
	name: string;
	status: string;
	client_status?: string | null;
	created_at?: string;
	updated_at?: string;
}

export interface Utterance {
	id: string;
	start: number;
	end: number;
	start_ms?: number;
	end_ms?: number;
	text: string;
	speaker: string;
	revision: number;
	state?: string;
	provisional?: boolean;
	segment_source?: string;
	source_channel?: "microphone" | "system" | null;
	updated_at?: string | null;
}

export interface TranscriptDelta {
	recording_id: string;
	revision: number;
	utterances: Utterance[];
	tombstones: string[];
}

export interface TranscriptState {
	recordingId: string;
	revision: number;
	utterances: Map<string, Utterance>;
	changeSerial: number;
	wordEvents: number;
}

export interface AppliedDelta {
	state: TranscriptState;
	changed: Utterance[];
	changedWords: number;
	needsSnapshot: boolean;
}

export interface AdvicePayload {
	action: AdviceAction;
	text: string;
	priority: AdvicePriority;
	reason: string;
}

const ACTIONS = new Set<AdviceAction>(["silent", "say", "ask", "watch"]);
const PRIORITIES = new Set<AdvicePriority>(["normal", "high"]);

export function countWords(text: string): number {
	return text.trim() ? text.trim().split(/\s+/u).length : 0;
}

export function isLiveRecording(recording: Recording): boolean {
	return (
		recording.status === "PAUSED" ||
		recording.client_status === "RECORDING" ||
		recording.client_status === "PAUSED"
	);
}

export function selectActiveRecording(recordings: Recording[]): Recording | undefined {
	const active = recordings.filter(isLiveRecording);
	return active.length === 1 ? active[0] : undefined;
}

export function createTranscriptState(recordingId: string): TranscriptState {
	return {
		recordingId,
		revision: 0,
		utterances: new Map(),
		changeSerial: 0,
		wordEvents: 0,
	};
}

export function applyTranscriptDelta(
	current: TranscriptState | undefined,
	delta: TranscriptDelta,
	mode: "snapshot" | "delta",
): AppliedDelta {
	const base = current?.recordingId === delta.recording_id ? current : createTranscriptState(delta.recording_id);

	if (mode === "delta" && delta.revision < base.revision) {
		return { state: base, changed: [], changedWords: 0, needsSnapshot: true };
	}
	if (mode === "delta" && delta.revision === base.revision) {
		return { state: base, changed: [], changedWords: 0, needsSnapshot: false };
	}

	const utterances = mode === "snapshot" ? new Map<string, Utterance>() : new Map(base.utterances);
	for (const id of delta.tombstones) utterances.delete(id);

	const changed: Utterance[] = [];
	for (const utterance of delta.utterances) {
		const previous = utterances.get(utterance.id);
		utterances.set(utterance.id, utterance);
		if (!previous || previous.revision !== utterance.revision || previous.text !== utterance.text) {
			changed.push(utterance);
		}
	}

	const changedWords = changed.reduce((total, utterance) => total + countWords(utterance.text), 0);
	const mutated = changed.length > 0 || delta.tombstones.length > 0 || mode === "snapshot";
	return {
		state: {
			recordingId: delta.recording_id,
			revision: delta.revision,
			utterances,
			changeSerial: base.changeSerial + (mutated ? 1 : 0),
			wordEvents: base.wordEvents + changedWords,
		},
		changed,
		changedWords,
		needsSnapshot: false,
	};
}

export function recentUtterances(
	state: TranscriptState,
	seconds: number,
	maxCharacters = 12_000,
): Utterance[] {
	const ordered = [...state.utterances.values()].sort(
		(left, right) => left.start - right.start || left.end - right.end || left.id.localeCompare(right.id),
	);
	if (ordered.length === 0) return [];

	const newestEnd = ordered[ordered.length - 1]?.end ?? 0;
	const cutoff = Math.max(0, newestEnd - seconds);
	const inWindow = ordered.filter((utterance) => utterance.end >= cutoff);
	const kept: Utterance[] = [];
	let characters = 0;
	for (let index = inWindow.length - 1; index >= 0; index -= 1) {
		const utterance = inWindow[index]!;
		characters += utterance.text.length;
		if (characters > maxCharacters && kept.length > 0) break;
		kept.push(utterance);
	}
	return kept.reverse();
}

export function shouldEvaluate(changed: Utterance[], pendingWords: number, thresholdWords: number): boolean {
	if (changed.some((utterance) => utterance.source_channel === "system" && /[?？]\s*$/u.test(utterance.text.trim()))) {
		return true;
	}
	if (
		changed.some(
			(utterance) =>
				utterance.provisional !== true &&
				utterance.state?.toUpperCase() !== "PROVISIONAL" &&
				countWords(utterance.text) >= 10,
		)
	) {
		return true;
	}
	return pendingWords >= thresholdWords;
}

export function parseAdvicePayload(value: unknown): AdvicePayload | undefined {
	if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
	const item = value as Record<string, unknown>;
	if (typeof item.action !== "string" || !ACTIONS.has(item.action as AdviceAction)) return undefined;
	if (typeof item.priority !== "string" || !PRIORITIES.has(item.priority as AdvicePriority)) return undefined;
	if (typeof item.text !== "string" || typeof item.reason !== "string") return undefined;

	const action = item.action as AdviceAction;
	const text = item.text.replace(/\s+/gu, " ").trim();
	if (action === "silent") {
		return { action, text: "", priority: item.priority as AdvicePriority, reason: item.reason.slice(0, 500) };
	}
	if (!text || text.length > 240) return undefined;
	return {
		action,
		text,
		priority: item.priority as AdvicePriority,
		reason: item.reason.slice(0, 500),
	};
}

export function parseAdviceText(text: string): AdvicePayload | undefined {
	const trimmed = text.trim().replace(/^```(?:json)?\s*/iu, "").replace(/\s*```$/u, "");
	try {
		return parseAdvicePayload(JSON.parse(trimmed));
	} catch {
		const start = trimmed.indexOf("{");
		const end = trimmed.lastIndexOf("}");
		if (start < 0 || end <= start) return undefined;
		try {
			return parseAdvicePayload(JSON.parse(trimmed.slice(start, end + 1)));
		} catch {
			return undefined;
		}
	}
}

export const ADVICE_TTL_MS: Record<Exclude<AdviceAction, "silent">, number> = {
	say: 30_000,
	ask: 60_000,
	watch: 120_000,
};

export function adviceExpired(advice: Advice | undefined, now = Date.now()): boolean {
	if (!advice || advice.action === "silent") return true;
	return now - advice.shownAt >= ADVICE_TTL_MS[advice.action];
}

export function inferenceIsStale(
	job: { recordingId: string; wordEvents: number },
	current: TranscriptState | undefined,
	wordThreshold = 20,
): boolean {
	return (
		!current ||
		current.recordingId !== job.recordingId ||
		current.wordEvents - job.wordEvents >= wordThreshold
	);
}

interface PendingRun<T, R> {
	input: T;
	resolve: (result: R | undefined) => void;
	reject: (error: unknown) => void;
}

/** Runs one task at a time and keeps only the newest waiting input. */
export class LatestOnlyRunner<T, R> {
	private pending?: PendingRun<T, R>;
	private active?: { controller: AbortController };
	private disposed = false;
	private readonly task: (input: T, signal: AbortSignal) => Promise<R>;

	constructor(task: (input: T, signal: AbortSignal) => Promise<R>) {
		this.task = task;
	}

	get isRunning(): boolean {
		return this.active !== undefined;
	}

	get hasPending(): boolean {
		return this.pending !== undefined;
	}

	enqueue(input: T, interrupt = false): Promise<R | undefined> {
		if (this.disposed) return Promise.resolve(undefined);
		this.pending?.resolve(undefined);
		const promise = new Promise<R | undefined>((resolve, reject) => {
			this.pending = { input, resolve, reject };
		});
		if (interrupt) this.active?.controller.abort();
		void this.drain();
		return promise;
	}

	dispose(): void {
		this.disposed = true;
		this.active?.controller.abort();
		this.pending?.resolve(undefined);
		this.pending = undefined;
	}

	private async drain(): Promise<void> {
		if (this.active || this.disposed) return;
		while (this.pending && !this.disposed) {
			const run = this.pending;
			this.pending = undefined;
			const controller = new AbortController();
			this.active = { controller };
			try {
				run.resolve(await this.task(run.input, controller.signal));
			} catch (error) {
				if (controller.signal.aborted) run.resolve(undefined);
				else run.reject(error);
			} finally {
				this.active = undefined;
			}
		}
	}
}

/** Small idempotent timer wrapper used by extension lifecycle. */
export class PollingLoop {
	private timer?: ReturnType<typeof setInterval>;

	get running(): boolean {
		return this.timer !== undefined;
	}

	start(intervalMs: number, poll: () => void): void {
		if (this.timer) return;
		poll();
		this.timer = setInterval(poll, intervalMs);
	}

	stop(): void {
		if (!this.timer) return;
		clearInterval(this.timer);
		this.timer = undefined;
	}
}
