import type { Recording, TranscriptDelta, Utterance } from "./state.ts";
import { isLiveRecording, selectActiveRecording } from "./state.ts";

export interface NojoinClientOptions {
	baseUrl: string;
	username?: string;
	password?: string;
	token?: string;
	requestTimeoutMs?: number;
	fetchImpl?: typeof fetch;
	now?: () => number;
}

export class NojoinError extends Error {
	readonly status?: number;
	readonly kind: "auth" | "network" | "response";

	constructor(message: string, status?: number, kind: "auth" | "network" | "response" = "response") {
		super(message);
		this.name = "NojoinError";
		this.status = status;
		this.kind = kind;
	}
}

interface LoginResponse {
	access_token: string;
	token_type: string;
	expires_in: number;
}

function normalizeBaseUrl(value: string): string {
	const url = new URL(value);
	if (url.protocol !== "https:") throw new Error("Nojoin URL must use HTTPS");
	return url.href.replace(/\/$/u, "");
}

function linkedSignal(parent: AbortSignal | undefined, timeoutMs: number): { signal: AbortSignal; clear: () => void } {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(new Error("request timeout")), timeoutMs);
	const abort = () => controller.abort(parent?.reason);
	parent?.addEventListener("abort", abort, { once: true });
	return {
		signal: controller.signal,
		clear: () => {
			clearTimeout(timeout);
			parent?.removeEventListener("abort", abort);
		},
	};
}

function asRecording(value: unknown): Recording | undefined {
	if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
	const item = value as Record<string, unknown>;
	if (typeof item.id !== "string" || typeof item.name !== "string" || typeof item.status !== "string") return undefined;
	return {
		id: item.id,
		name: item.name,
		status: item.status,
		client_status: typeof item.client_status === "string" ? item.client_status : null,
		created_at: typeof item.created_at === "string" ? item.created_at : undefined,
		updated_at: typeof item.updated_at === "string" ? item.updated_at : undefined,
	};
}

function asUtterance(value: unknown): Utterance | undefined {
	if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
	const item = value as Record<string, unknown>;
	if (
		typeof item.id !== "string" ||
		typeof item.start !== "number" ||
		typeof item.end !== "number" ||
		typeof item.text !== "string" ||
		typeof item.speaker !== "string" ||
		typeof item.revision !== "number"
	) {
		return undefined;
	}
	return {
		id: item.id,
		start: item.start,
		end: item.end,
		start_ms: typeof item.start_ms === "number" ? item.start_ms : undefined,
		end_ms: typeof item.end_ms === "number" ? item.end_ms : undefined,
		text: item.text,
		speaker: item.speaker,
		revision: item.revision,
		state: typeof item.state === "string" ? item.state : undefined,
		provisional: item.provisional === true,
		segment_source: typeof item.segment_source === "string" ? item.segment_source : undefined,
		source_channel:
			item.source_channel === "microphone" || item.source_channel === "system" ? item.source_channel : null,
		updated_at: typeof item.updated_at === "string" ? item.updated_at : null,
	};
}

export function parseTranscriptDelta(value: unknown): TranscriptDelta {
	if (!value || typeof value !== "object" || Array.isArray(value)) throw new NojoinError("Invalid transcript response");
	const item = value as Record<string, unknown>;
	if (
		typeof item.recording_id !== "string" ||
		!Number.isSafeInteger(item.revision) ||
		!Array.isArray(item.utterances) ||
		!Array.isArray(item.tombstones)
	) {
		throw new NojoinError("Invalid transcript response");
	}
	const utterances = item.utterances.map(asUtterance);
	if (utterances.some((utterance) => !utterance) || item.tombstones.some((id) => typeof id !== "string")) {
		throw new NojoinError("Invalid transcript response");
	}
	return {
		recording_id: item.recording_id,
		revision: item.revision as number,
		utterances: utterances as Utterance[],
		tombstones: item.tombstones as string[],
	};
}

export class NojoinClient {
	readonly baseUrl: string;
	private readonly username?: string;
	private readonly password?: string;
	private readonly suppliedToken?: string;
	private readonly requestTimeoutMs: number;
	private readonly fetchImpl: typeof fetch;
	private readonly now: () => number;
	private token?: string;
	private tokenExpiresAt = 0;

	constructor(options: NojoinClientOptions) {
		this.baseUrl = normalizeBaseUrl(options.baseUrl);
		this.username = options.username;
		this.password = options.password;
		this.suppliedToken = options.token;
		this.requestTimeoutMs = options.requestTimeoutMs ?? 10_000;
		this.fetchImpl = options.fetchImpl ?? fetch;
		this.now = options.now ?? Date.now;
		if (this.suppliedToken) {
			this.token = this.suppliedToken;
			this.tokenExpiresAt = Number.POSITIVE_INFINITY;
		}
	}

	get authenticationState(): "token" | "credentials" | "needed" {
		if (this.token && this.tokenExpiresAt > this.now()) return "token";
		if (this.username && this.password) return "credentials";
		return "needed";
	}

	clearToken(): void {
		this.token = undefined;
		this.tokenExpiresAt = 0;
	}

	async authenticate(signal?: AbortSignal): Promise<void> {
		if (this.token && this.tokenExpiresAt - this.now() > 30_000) return;
		if (this.suppliedToken) {
			this.token = this.suppliedToken;
			this.tokenExpiresAt = Number.POSITIVE_INFINITY;
			return;
		}
		if (!this.username || !this.password) {
			throw new NojoinError("Nojoin credentials are required", 401, "auth");
		}

		const body = new URLSearchParams({ username: this.username, password: this.password });
		const response = await this.fetchRaw(
			"/api/v1/login/access-token",
			{
				method: "POST",
				headers: { "content-type": "application/x-www-form-urlencoded" },
				body,
			},
			signal,
		);
		if (!response.ok) throw new NojoinError("Nojoin authentication failed", response.status, "auth");
		const payload = (await response.json()) as Partial<LoginResponse>;
		if (
			typeof payload.access_token !== "string" ||
			payload.token_type?.toLowerCase() !== "bearer" ||
			typeof payload.expires_in !== "number" ||
			payload.expires_in <= 0
		) {
			throw new NojoinError("Invalid Nojoin login response", response.status, "auth");
		}
		this.token = payload.access_token;
		this.tokenExpiresAt = this.now() + payload.expires_in * 1000;
	}

	async listActiveRecordings(signal?: AbortSignal): Promise<Recording[]> {
		const value = await this.requestJson(
			"/api/v1/recordings?limit=20&status=UPLOADING&status=PAUSED",
			{},
			signal,
		);
		if (!Array.isArray(value)) throw new NojoinError("Invalid recordings response");
		const recordings = value.map(asRecording);
		if (recordings.some((recording) => !recording)) throw new NojoinError("Invalid recordings response");
		return (recordings as Recording[]).filter(isLiveRecording);
	}

	async discoverActiveRecording(signal?: AbortSignal): Promise<Recording | undefined> {
		const recordings = await this.listActiveRecordings(signal);
		if (recordings.length > 1) {
			throw new NojoinError("Multiple live recordings found; use a manual recording override");
		}
		return selectActiveRecording(recordings);
	}

	async getRecording(recordingId: string, signal?: AbortSignal): Promise<Recording> {
		const recording = asRecording(
			await this.requestJson(`/api/v1/recordings/${encodeURIComponent(recordingId)}`, {}, signal),
		);
		if (!recording) throw new NojoinError("Invalid recording response");
		return recording;
	}

	async getUtterances(recordingId: string, afterRevision?: number, signal?: AbortSignal): Promise<TranscriptDelta> {
		const suffix = afterRevision === undefined ? "" : `?after_revision=${afterRevision}`;
		return parseTranscriptDelta(
			await this.requestJson(
				`/api/v1/transcripts/${encodeURIComponent(recordingId)}/utterances${suffix}`,
				{},
				signal,
			),
		);
	}

	private async requestJson(path: string, init: RequestInit, signal?: AbortSignal): Promise<unknown> {
		await this.authenticate(signal);
		let response = await this.fetchRaw(
			path,
			{ ...init, headers: { ...init.headers, authorization: `Bearer ${this.token}` } },
			signal,
		);
		if (response.status === 401 && !this.suppliedToken) {
			this.clearToken();
			await this.authenticate(signal);
			response = await this.fetchRaw(
				path,
				{ ...init, headers: { ...init.headers, authorization: `Bearer ${this.token}` } },
				signal,
			);
		}
		if (response.status === 401 || response.status === 403) {
			this.clearToken();
			throw new NojoinError("Nojoin authentication is required", response.status, "auth");
		}
		if (!response.ok) throw new NojoinError(`Nojoin request failed (${response.status})`, response.status);
		try {
			return await response.json();
		} catch {
			throw new NojoinError("Invalid JSON from Nojoin", response.status);
		}
	}

	private async fetchRaw(path: string, init: RequestInit, signal?: AbortSignal): Promise<Response> {
		const linked = linkedSignal(signal, this.requestTimeoutMs);
		try {
			return await this.fetchImpl(`${this.baseUrl}${path}`, { ...init, signal: linked.signal });
		} catch (error) {
			if (signal?.aborted) throw error;
			throw new NojoinError("Nojoin is unreachable", undefined, "network");
		} finally {
			linked.clear();
		}
	}
}
