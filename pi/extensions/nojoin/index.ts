import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

import { requestAdvice, requestRollingContext, resolveAdviserModel, type ResolvedModel } from "./adviser.ts";
import { NojoinClient, NojoinError } from "./nojoin.ts";
import { buildDirectChatContext } from "./prompt.ts";
import {
	adviceExpired,
	applyTranscriptDelta,
	inferenceIsStale,
	isLiveRecording,
	LatestOnlyRunner,
	PollingLoop,
	recentUtterances,
	shouldEvaluate,
	type Advice,
	type Recording,
	type TranscriptState,
	type Utterance,
} from "./state.ts";
import { formatTime, updateWidget, type WidgetMode } from "./ui.ts";

interface Config {
	nojoinUrl: string;
	pollIntervalMs: number;
	autoStart: boolean;
	automaticModel?: string;
	manualModel?: string;
	recentContextSeconds: number;
	adviceEnabled: boolean;
	triggerWords: number;
	summaryWords: number;
	requestTimeoutMs: number;
	debug: boolean;
}

interface AdviceJob {
	kind: "advice";
	manual: boolean;
	recordingId: string;
	revision: number;
	wordEvents: number;
	focus: string;
	brief: string;
	rollingContext: string;
	recent: Utterance[];
	newestIds: Set<string>;
	previousAdvice: Advice[];
	pollReceivedAt: number;
}

interface SummaryJob {
	kind: "summary";
	recordingId: string;
	revision: number;
	wordEvents: number;
	focus: string;
	rollingContext: string;
	recent: Utterance[];
}

type InferenceJob = AdviceJob | SummaryJob;
type InferenceResult =
	| { kind: "advice"; job: AdviceJob; payload: Awaited<ReturnType<typeof requestAdvice>>; startedAt: number; finishedAt: number }
	| { kind: "summary"; job: SummaryJob; context: string; startedAt: number; finishedAt: number };

const DEFAULT_CONFIG: Config = {
	nojoinUrl: "https://nojoin.kit",
	pollIntervalMs: 3_000,
	autoStart: false,
	recentContextSeconds: 180,
	adviceEnabled: true,
	triggerWords: 24,
	summaryWords: 300,
	requestTimeoutMs: 10_000,
	debug: false,
};
const CONFIG_PATH = join(dirname(fileURLToPath(import.meta.url)), "config.json");
const BRIEF_MAX_CHARACTERS = 40_000;
const SUBCOMMANDS = [
	"start",
	"stop",
	"status",
	"focus",
	"focus-clear",
	"brief",
	"brief-clear",
	"help",
	"recording",
	"auto",
	"clear",
	"debug",
];

function loadConfig(): Config {
	let file: Partial<Config> = {};
	try {
		file = JSON.parse(readFileSync(CONFIG_PATH, "utf8")) as Partial<Config>;
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code !== "ENOENT") console.error("[nojoin] Invalid config.json; using defaults");
	}
	return {
		...DEFAULT_CONFIG,
		...file,
		nojoinUrl: process.env.NOJOIN_URL || file.nojoinUrl || DEFAULT_CONFIG.nojoinUrl,
		pollIntervalMs: Math.max(1_000, Number(file.pollIntervalMs ?? DEFAULT_CONFIG.pollIntervalMs)),
		recentContextSeconds: Math.max(60, Number(file.recentContextSeconds ?? DEFAULT_CONFIG.recentContextSeconds)),
		triggerWords: Math.max(8, Number(file.triggerWords ?? DEFAULT_CONFIG.triggerWords)),
		summaryWords: Math.max(100, Number(file.summaryWords ?? DEFAULT_CONFIG.summaryWords)),
		requestTimeoutMs: Math.max(2_000, Number(file.requestTimeoutMs ?? DEFAULT_CONFIG.requestTimeoutMs)),
	};
}

function safeError(error: unknown): string {
	if (error instanceof NojoinError) return error.message;
	if (!(error instanceof Error)) return "Unexpected adviser error";
	if (/aborted/iu.test(error.message)) return "Request cancelled";
	return error.message
		.replace(/\bBearer\s+\S+/giu, "Bearer [redacted]")
		.replace(/((?:api[_ -]?key|authorization|token|password)\s*[:=]\s*)\S+/giu, "$1[redacted]")
		.replace(/\s+/gu, " ")
		.trim()
		.slice(0, 500) || "Unexpected adviser error";
}

export default function nojoinExtension(pi: ExtensionAPI): void {
	let config = loadConfig();
	let context: ExtensionContext | undefined;
	let client: NojoinClient | undefined;
	let enabled = false;
	let widgetMode: WidgetMode = "idle";
	let activeRecording: Recording | undefined;
	let manualRecordingId: string | undefined;
	let transcript: TranscriptState | undefined;
	let advice: Advice | undefined;
	let quietMessage: string | undefined;
	let previousAdvice: Advice[] = [];
	let focus = "";
	let brief = "";
	let briefPath: string | undefined;
	let rollingContext = "";
	let pendingWords = 0;
	let wordsSinceAdvice = 0;
	let wordsSinceSummary = 0;
	let lastPollAt: number | undefined;
	let lastInferenceAt: number | undefined;
	let lastInferenceStartedAt: number | undefined;
	let lastWidgetAt: number | undefined;
	let lastError: string | undefined;
	let retryAt = 0;
	let consecutiveFailures = 0;
	let pollPromise: Promise<void> | undefined;
	let pollPromiseGeneration = 0;
	let pollController: AbortController | undefined;
	let generation = 0;
	let runner: LatestOnlyRunner<InferenceJob, InferenceResult> | undefined;
	let automaticModel: ResolvedModel | undefined;
	let manualModel: ResolvedModel | undefined;
	let manualInFlight = false;
	let debug = config.debug;
	const pollingLoop = new PollingLoop();
	let modelSessionId = randomUUID();

	const log = (message: string, fields: Record<string, unknown> = {}) => {
		if (!debug) return;
		console.error(`[nojoin] ${message} ${JSON.stringify(fields)}`);
	};

	const render = () => {
		if (!context) return;
		if (advice && adviceExpired(advice)) advice = undefined;
		updateWidget(context, { enabled, mode: widgetMode, advice, history: previousAdvice, message: quietMessage });
		lastWidgetAt = Date.now();
	};

	const clearMeeting = () => {
		activeRecording = undefined;
		transcript = undefined;
		advice = undefined;
		quietMessage = undefined;
		previousAdvice = [];
		rollingContext = "";
		pendingWords = 0;
		wordsSinceAdvice = 0;
		wordsSinceSummary = 0;
		modelSessionId = randomUUID();
		widgetMode = "idle";
	};

	const beginMeeting = (recording: Recording) => {
		clearMeeting();
		activeRecording = recording;
		transcript = undefined;
		widgetMode = "listening";
		log("meeting detected", { recordingId: recording.id, title: recording.name });
		render();
	};

	const runJob = async (job: InferenceJob, signal: AbortSignal): Promise<InferenceResult> => {
		if (!context) throw new Error("Adviser context unavailable");
		const startedAt = Date.now();
		lastInferenceStartedAt = startedAt;
		quietMessage = undefined;
		widgetMode = "thinking";
		render();
		log("inference start", {
			kind: job.kind,
			revision: job.revision,
			startedAt,
			pollReceivedAt: job.kind === "advice" ? job.pollReceivedAt : undefined,
			detectionDelayMs: job.kind === "advice" ? startedAt - job.pollReceivedAt : undefined,
		});

		if (job.kind === "summary") {
			if (!automaticModel) throw new Error("No adviser model available");
			const summary = await requestRollingContext(
				context,
				automaticModel,
				job.rollingContext,
				job.focus,
				job.recent,
				signal,
				modelSessionId,
			);
			return { kind: "summary", job, context: summary, startedAt, finishedAt: Date.now() };
		}

		const resolved = job.manual ? manualModel : automaticModel;
		if (!resolved) throw new Error("No adviser model available");
		const payload = await requestAdvice(
			context,
			resolved,
			{
				mode: job.manual ? "manual" : "automatic",
				focus: job.focus,
				brief: job.brief,
				rollingContext: job.rollingContext,
				recent: job.recent,
				newestIds: job.newestIds,
				previousAdvice: job.previousAdvice,
			},
			signal,
			modelSessionId,
		);
		return { kind: "advice", job, payload, startedAt, finishedAt: Date.now() };
	};

	const handleInferenceResult = (result: InferenceResult | undefined) => {
		if (!result) return;
		lastInferenceAt = result.finishedAt;
		lastError = undefined;
		log("inference end", {
			kind: result.kind,
			revision: result.job.revision,
			startedAt: result.startedAt,
			finishedAt: result.finishedAt,
			durationMs: result.finishedAt - result.startedAt,
		});

		if (result.kind === "summary") {
			if (activeRecording?.id === result.job.recordingId) {
				rollingContext = result.context;
				wordsSinceSummary = Math.max(0, (transcript?.wordEvents ?? result.job.wordEvents) - result.job.wordEvents);
			}
			widgetMode = activeRecording ? "listening" : "idle";
			render();
			return;
		}

		if (result.job.brief !== brief) {
			log("discarded advice from replaced brief", { revision: result.job.revision });
			widgetMode = activeRecording ? "listening" : "idle";
			render();
			return;
		}
		if (!result.job.manual && inferenceIsStale(result.job, transcript)) {
			log("discarded stale advice", { revision: result.job.revision, currentRevision: transcript?.revision });
			widgetMode = activeRecording ? "listening" : "idle";
			render();
			return;
		}
		if (activeRecording?.id !== result.job.recordingId) return;

		if (result.payload.action === "silent") {
			advice = undefined;
			quietMessage = result.job.manual ? "Checked transcript · no useful suggestion" : undefined;
		} else {
			quietMessage = undefined;
			advice = {
				...result.payload,
				recordingId: result.job.recordingId,
				revision: result.job.revision,
				shownAt: Date.now(),
				manual: result.job.manual,
			};
			previousAdvice = [...previousAdvice.slice(-4), advice];
			wordsSinceAdvice = 0;
		}
		widgetMode = "listening";
		log("advice", { action: result.payload.action, priority: result.payload.priority });
		render();
		log("widget update", { updatedAt: lastWidgetAt, revision: result.job.revision });
	};

	const handleModelFailure = (error: unknown) => {
		if (/aborted|cancelled/iu.test(error instanceof Error ? error.message : "")) return;
		lastError = safeError(error);
		quietMessage = "Adviser failed · run /nojoin status";
		widgetMode = activeRecording ? "listening" : "idle";
		if (adviceExpired(advice)) advice = undefined;
		log("model failure", { error: lastError });
		render();
	};

	const queueAdvice = (manual: boolean, newest: Utterance[]): Promise<InferenceResult | undefined> | undefined => {
		if (!runner || !activeRecording || !transcript) return undefined;
		const seconds = manual ? Math.min(config.recentContextSeconds, 120) : config.recentContextSeconds;
		const job: AdviceJob = {
			kind: "advice",
			manual,
			recordingId: activeRecording.id,
			revision: transcript.revision,
			wordEvents: transcript.wordEvents,
			focus,
			brief,
			rollingContext,
			recent: recentUtterances(transcript, seconds),
			newestIds: new Set(newest.map((utterance) => utterance.id)),
			previousAdvice: [...previousAdvice],
			pollReceivedAt: lastPollAt ?? Date.now(),
		};
		const promise = runner.enqueue(job, manual);
		if (!manual) {
			void promise.then(handleInferenceResult).catch(handleModelFailure);
		}
		return promise;
	};

	const maybeQueueSummary = () => {
		if (
			!runner ||
			runner.isRunning ||
			runner.hasPending ||
			manualInFlight ||
			!automaticModel ||
			!activeRecording ||
			!transcript ||
			wordsSinceSummary < config.summaryWords
		) {
			return;
		}
		const job: SummaryJob = {
			kind: "summary",
			recordingId: activeRecording.id,
			revision: transcript.revision,
			wordEvents: transcript.wordEvents,
			focus,
			rollingContext,
			recent: recentUtterances(transcript, Math.max(config.recentContextSeconds, 300), 18_000),
		};
		void runner.enqueue(job).then(handleInferenceResult).catch(handleModelFailure);
	};

	const recordPollFailure = (error: unknown, expectedGeneration: number) => {
		if (expectedGeneration !== generation || pollController?.signal.aborted) return;
		consecutiveFailures += 1;
		const auth = error instanceof NojoinError && error.kind === "auth";
		const delay = auth
			? Math.min(300_000, 30_000 * 2 ** Math.min(4, consecutiveFailures - 1))
			: Math.min(60_000, 3_000 * 2 ** Math.min(4, consecutiveFailures - 1));
		retryAt = Date.now() + delay;
		lastError = safeError(error);
		widgetMode = auth ? "auth" : "degraded";
		if (adviceExpired(advice)) advice = undefined;
		log("poll failure", { error: lastError, retryMs: delay });
		render();
	};

	const poll = async (expectedGeneration: number) => {
		const thisClient = client;
		const controller = pollController;
		if (
			expectedGeneration !== generation ||
			!enabled ||
			!thisClient ||
			!controller ||
			Date.now() < retryAt
		) {
			if (advice && adviceExpired(advice)) render();
			return;
		}

		try {
			const signal = controller.signal;
			const recording = manualRecordingId
				? await thisClient.getRecording(manualRecordingId, signal)
				: await thisClient.discoverActiveRecording(signal);
			if (expectedGeneration !== generation || signal.aborted) return;
			const liveRecording = recording && isLiveRecording(recording) ? recording : undefined;
			if (!liveRecording) {
				if (activeRecording) {
					log("meeting ended", { recordingId: activeRecording.id });
					clearMeeting();
				}
				lastPollAt = Date.now();
				consecutiveFailures = 0;
				retryAt = 0;
				render();
				return;
			}

			if (activeRecording?.id !== liveRecording.id) beginMeeting(liveRecording);
			else activeRecording = liveRecording;

			const before = transcript;
			const mode = before ? "delta" : "snapshot";
			let delta = await thisClient.getUtterances(liveRecording.id, before?.revision, signal);
			if (expectedGeneration !== generation || signal.aborted) return;
			let applied = applyTranscriptDelta(before, delta, mode);
			if (applied.needsSnapshot) {
				delta = await thisClient.getUtterances(liveRecording.id, undefined, signal);
				if (expectedGeneration !== generation || signal.aborted) return;
				applied = applyTranscriptDelta(undefined, delta, "snapshot");
			}
			transcript = applied.state;
			lastPollAt = Date.now();
			consecutiveFailures = 0;
			retryAt = 0;
			widgetMode = "listening";
			if (applied.changedWords > 0) quietMessage = undefined;
			pendingWords += applied.changedWords;
			wordsSinceAdvice += applied.changedWords;
			wordsSinceSummary += applied.changedWords;
			if (
				advice &&
				(adviceExpired(advice) ||
					(advice.action === "say" && wordsSinceAdvice >= 18) ||
					(advice.action === "ask" && wordsSinceAdvice >= 40))
			) {
				advice = undefined;
			}

			log("poll", {
				revision: transcript.revision,
				utterances: applied.changed.length,
				newestUtteranceUpdatedAt: applied.changed.at(-1)?.updated_at,
				receivedAt: lastPollAt,
			});

			if (
				config.adviceEnabled &&
				automaticModel &&
				!manualInFlight &&
				shouldEvaluate(applied.changed, pendingWords, config.triggerWords)
			) {
				pendingWords = 0;
				queueAdvice(false, applied.changed);
			} else {
				maybeQueueSummary();
			}
			render();
		} catch (error) {
			recordPollFailure(error, expectedGeneration);
		}
	};

	const pollNow = (): Promise<void> => {
		if (pollPromise && pollPromiseGeneration === generation) return pollPromise;
		const expectedGeneration = generation;
		const pending = poll(expectedGeneration).finally(() => {
			if (pollPromise === pending) pollPromise = undefined;
		});
		pollPromise = pending;
		pollPromiseGeneration = expectedGeneration;
		return pending;
	};

	const start = async (ctx: ExtensionContext) => {
		if (enabled) {
			await pollNow();
			return;
		}
		config = loadConfig();
		debug = config.debug;
		context = ctx;
		generation += 1;
		client = new NojoinClient({
			baseUrl: config.nojoinUrl,
			username: process.env.NOJOIN_USERNAME,
			password: process.env.NOJOIN_PASSWORD,
			token: process.env.NOJOIN_TOKEN,
			requestTimeoutMs: config.requestTimeoutMs,
		});
		automaticModel = resolveAdviserModel(ctx, config.automaticModel);
		manualModel = resolveAdviserModel(ctx, config.manualModel) ?? automaticModel;
		enabled = true;
		widgetMode = "idle";
		pollController = new AbortController();
		runner = new LatestOnlyRunner(runJob);
		render();
		pollingLoop.start(config.pollIntervalMs, () => void pollNow());
		await pollNow();
	};

	const stop = () => {
		generation += 1;
		enabled = false;
		pollingLoop.stop();
		pollController?.abort();
		pollController = undefined;
		runner?.dispose();
		runner = undefined;
		client?.clearToken();
		client = undefined;
		pollPromise = undefined;
		brief = "";
		briefPath = undefined;
		clearMeeting();
		widgetMode = "idle";
		render();
	};

	const helpNow = async (ctx: ExtensionContext) => {
		if (!enabled) await start(ctx);
		await pollNow();
		if (!activeRecording || !transcript || transcript.utterances.size === 0) {
			ctx.ui.notify("No live transcript is available", "warning");
			return;
		}
		manualInFlight = true;
		try {
			const result = await queueAdvice(true, recentUtterances(transcript, 120));
			handleInferenceResult(result);
			if (result?.kind === "advice" && result.payload.action === "silent") {
				ctx.ui.notify("Adviser checked transcript but found no useful suggestion", "info");
			}
		} catch (error) {
			handleModelFailure(error);
			ctx.ui.notify(lastError || "Manual adviser failed", "warning");
		} finally {
			manualInFlight = false;
		}
	};

	const statusText = () =>
		[
			`enabled: ${enabled}`,
			`Nojoin URL: ${config.nojoinUrl}`,
			`authentication: ${client?.authenticationState ?? "not connected"}`,
			`recording: ${activeRecording ? `${activeRecording.id} (${activeRecording.name})` : "none"}`,
			`selection: ${manualRecordingId ? `manual ${manualRecordingId}` : "automatic"}`,
			`transcript revision: ${transcript?.revision ?? "none"}`,
			`utterances buffered: ${transcript?.utterances.size ?? 0}`,
			`last poll: ${formatTime(lastPollAt)}`,
			`last inference start: ${formatTime(lastInferenceStartedAt)}`,
			`last inference finish: ${formatTime(lastInferenceAt)}`,
			`last widget update: ${formatTime(lastWidgetAt)}`,
			`automatic model: ${automaticModel?.name ?? "unavailable"}`,
			`manual model: ${manualModel?.name ?? "unavailable"}`,
			`focus: ${focus || "none"}`,
			`brief: ${briefPath ? `${basename(briefPath)} (${brief.length} characters)` : "none"}`,
			`inference: ${runner?.isRunning ? "running" : "idle"}${runner?.hasPending ? ", newest state pending" : ""}`,
			`last result: ${advice?.action.toUpperCase() || quietMessage || previousAdvice.at(-1)?.action.toUpperCase() || "none"}`,
			`last error: ${lastError || "none"}`,
			`debug: ${debug}`,
		].join("\n");

	pi.registerCommand("nojoin", {
		description: "Control the Nojoin live meeting adviser",
		getArgumentCompletions: (prefix) => {
			const items = SUBCOMMANDS.filter((item) => item.startsWith(prefix)).map((item) => ({ value: item, label: item }));
			return items.length ? items : null;
		},
		handler: async (rawArgs, ctx) => {
			context = ctx;
			const args = rawArgs.trim();
			const [command = "status", ...rest] = args.split(/\s+/u);
			const value = rest.join(" ").trim();
			switch (command) {
				case "start":
					await start(ctx);
					break;
				case "stop":
					stop();
					break;
				case "status":
				case "":
					ctx.ui.notify(statusText(), "info");
					break;
				case "focus":
					if (!value) ctx.ui.notify(`Current focus: ${focus || "none"}`, "info");
					else {
						focus = value.slice(0, 1_000);
						ctx.ui.notify("Meeting focus set", "info");
					}
					break;
				case "focus-clear":
					focus = "";
					ctx.ui.notify("Meeting focus cleared", "info");
					break;
				case "brief":
					if (!value) {
						ctx.ui.notify(
							briefPath ? `Brief loaded: ${basename(briefPath)} (${brief.length} characters)` : "No brief loaded",
							"info",
						);
						break;
					}
					try {
						const unquoted =
							(value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))
								? value.slice(1, -1)
								: value;
						const expanded =
							unquoted === "~" ? homedir() : unquoted.startsWith("~/") ? join(homedir(), unquoted.slice(2)) : unquoted;
						const source = resolve(ctx.cwd, expanded);
						const loaded = readFileSync(source, "utf8").trim();
						if (!loaded) throw new Error("Brief file is empty");
						if (loaded.includes("\0")) throw new Error("Brief must be a plain-text or Markdown file");
						if (loaded.length > BRIEF_MAX_CHARACTERS) {
							throw new Error(`Brief exceeds ${BRIEF_MAX_CHARACTERS.toLocaleString()} characters`);
						}
						brief = loaded;
						briefPath = source;
						advice = undefined;
						previousAdvice = [];
						quietMessage = `Brief loaded · ${basename(source)}`;
						render();
						ctx.ui.notify(`Brief loaded: ${basename(source)} (${loaded.length} characters)`, "info");
					} catch (error) {
						ctx.ui.notify(safeError(error), "warning");
					}
					break;
				case "brief-clear":
					brief = "";
					briefPath = undefined;
					advice = undefined;
					previousAdvice = [];
					quietMessage = "Meeting brief cleared";
					render();
					ctx.ui.notify("Meeting brief cleared", "info");
					break;
				case "help":
					await helpNow(ctx);
					break;
				case "recording":
					if (!value) {
						ctx.ui.notify("Usage: /nojoin recording RECORDING_ID", "warning");
						break;
					}
					manualRecordingId = value;
					clearMeeting();
					if (enabled) await pollNow();
					break;
				case "auto":
					manualRecordingId = undefined;
					clearMeeting();
					if (enabled) await pollNow();
					break;
				case "clear":
					advice = undefined;
					previousAdvice = [];
					quietMessage = undefined;
					render();
					break;
				case "debug":
					debug = value === "on" ? true : value === "off" ? false : !debug;
					ctx.ui.notify(`Nojoin debug ${debug ? "on" : "off"}`, "info");
					break;
				default:
					ctx.ui.notify(`Unknown subcommand: ${command}`, "warning");
			}
		},
	});

	pi.registerShortcut("ctrl+alt+h", {
		description: "Nojoin: help me now",
		handler: helpNow,
	});

	pi.on("before_agent_start", async (event) => {
		if (!enabled) return;
		await pollNow();
		if (!activeRecording || !transcript) return;
		return {
			systemPrompt: `${event.systemPrompt}\n\n${buildDirectChatContext({
				recordingName: activeRecording.name,
				focus,
				brief,
				rollingContext,
				recent: recentUtterances(transcript, config.recentContextSeconds, 18_000),
			})}`,
		};
	});

	pi.on("session_start", async (_event, ctx) => {
		context = ctx;
		config = loadConfig();
		debug = config.debug;
		if (config.autoStart) await start(ctx);
	});

	pi.on("session_shutdown", async () => {
		stop();
		context = undefined;
	});
}
