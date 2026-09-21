import assert from "node:assert/strict";
import test from "node:test";

import { NojoinClient, NojoinError, parseTranscriptDelta } from "../nojoin.ts";
import { ADVISER_SYSTEM_PROMPT, buildAdvicePrompt, buildDirectChatContext } from "../prompt.ts";
import {
	adviceExpired,
	applyTranscriptDelta,
	createTranscriptState,
	inferenceIsStale,
	LatestOnlyRunner,
	parseAdvicePayload,
	parseAdviceText,
	PollingLoop,
	selectActiveRecording,
	type TranscriptDelta,
	type Utterance,
} from "../state.ts";

const utterance = (id: string, text = "hello there", revision = 1): Utterance => ({
	id,
	start: revision,
	end: revision + 1,
	text,
	speaker: "Unknown",
	revision,
	state: "STABLE",
	source_channel: "system",
});

const delta = (revision: number, utterances: Utterance[], tombstones: string[] = []): TranscriptDelta => ({
	recording_id: "rec-1",
	revision,
	utterances,
	tombstones,
});

test("applies snapshots, replacements, tombstones, and revision advancement", () => {
	const initial = applyTranscriptDelta(undefined, delta(2, [utterance("u1"), utterance("u2")]), "snapshot");
	const changed = applyTranscriptDelta(initial.state, delta(4, [utterance("u1", "corrected text", 2)], ["u2"]), "delta");
	assert.equal(changed.state.revision, 4);
	assert.equal(changed.state.utterances.get("u1")?.text, "corrected text");
	assert.equal(changed.state.utterances.has("u2"), false);
	assert.equal(changed.changed.length, 1);
});

test("ignores duplicate deltas and requests a snapshot for a regressed revision", () => {
	const state = applyTranscriptDelta(undefined, delta(3, [utterance("u1")]), "snapshot").state;
	const duplicate = applyTranscriptDelta(state, delta(3, [utterance("u2")]), "delta");
	assert.strictEqual(duplicate.state, state);
	assert.equal(duplicate.changed.length, 0);
	assert.equal(applyTranscriptDelta(state, delta(2, []), "delta").needsSnapshot, true);
});

test("validates transcript responses", () => {
	assert.equal(parseTranscriptDelta(delta(1, [utterance("u1")])).revision, 1);
	assert.throws(() => parseTranscriptDelta({ revision: "bad" }), NojoinError);
});

test("validates adviser output and treats silent text as empty", () => {
	assert.deepEqual(
		parseAdvicePayload({ action: "silent", text: "filler", priority: "normal", reason: "nothing useful" }),
		{ action: "silent", text: "", priority: "normal", reason: "nothing useful" },
	);
	assert.equal(parseAdvicePayload({ action: "say", text: "", priority: "normal", reason: "x" }), undefined);
	assert.equal(parseAdviceText("not json"), undefined);
	assert.equal(parseAdviceText('```json\n{"action":"ask","text":"Who owns this?","priority":"high","reason":"No owner"}\n```')?.action, "ask");
});

test("expires advice by action lifetime", () => {
	const base = {
		text: "Useful",
		priority: "normal" as const,
		reason: "test",
		recordingId: "rec-1",
		revision: 1,
		shownAt: 1_000,
		manual: false,
	};
	assert.equal(adviceExpired({ ...base, action: "say" }, 31_000), true);
	assert.equal(adviceExpired({ ...base, action: "watch" }, 31_000), false);
});

test("coalesces waiting inference to newest input", async () => {
	let release!: () => void;
	const firstGate = new Promise<void>((resolve) => {
		release = resolve;
	});
	const started: number[] = [];
	const runner = new LatestOnlyRunner<number, number>(async (value) => {
		started.push(value);
		if (value === 1) await firstGate;
		return value * 10;
	});
	const first = runner.enqueue(1);
	const obsolete = runner.enqueue(2);
	const newest = runner.enqueue(3);
	release();
	assert.equal(await first, 10);
	assert.equal(await obsolete, undefined);
	assert.equal(await newest, 30);
	assert.deepEqual(started, [1, 3]);
	runner.dispose();
});

test("interrupts running inference for manual help", async () => {
	const runner = new LatestOnlyRunner<string, string>(
		(input, signal) =>
			new Promise((resolve, reject) => {
				if (input === "manual") return resolve(input);
				signal.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
			}),
	);
	const automatic = runner.enqueue("automatic");
	const manual = runner.enqueue("manual", true);
	assert.equal(await automatic, undefined);
	assert.equal(await manual, "manual");
	runner.dispose();
});

test("suppresses inference after substantial newer speech", () => {
	const state = createTranscriptState("rec-1");
	state.wordEvents = 45;
	assert.equal(inferenceIsStale({ recordingId: "rec-1", wordEvents: 20 }, state), true);
	assert.equal(inferenceIsStale({ recordingId: "rec-1", wordEvents: 30 }, state), false);
	assert.equal(inferenceIsStale({ recordingId: "other", wordEvents: 45 }, state), true);
});

test("polling lifecycle is idempotent and cleanup permits a clean reload", async () => {
	let calls = 0;
	const oldLoop = new PollingLoop();
	oldLoop.start(5, () => calls++);
	oldLoop.start(5, () => calls += 100);
	await new Promise((resolve) => setTimeout(resolve, 12));
	oldLoop.stop();
	const afterStop = calls;
	await new Promise((resolve) => setTimeout(resolve, 10));
	assert.equal(calls, afterStop);

	const newLoop = new PollingLoop();
	newLoop.start(5, () => calls++);
	assert.equal(calls, afterStop + 1);
	newLoop.stop();
});

test("selects exactly one real live browser capture and tracks changes", () => {
	const first = { id: "one", name: "One", status: "UPLOADING", client_status: "RECORDING" };
	const second = { id: "two", name: "Two", status: "PAUSED", client_status: null };
	const imported = { id: "file", name: "Import", status: "UPLOADING", client_status: null };
	assert.equal(selectActiveRecording([first, imported])?.id, "one");
	assert.equal(selectActiveRecording([second])?.id, "two");
	assert.equal(selectActiveRecording([first, second]), undefined);
});

test("reauthenticates after token expiry without exposing credentials", async () => {
	let now = 0;
	let loginCount = 0;
	const headers: string[] = [];
	const fakeFetch = async (_url: string | URL | Request, init?: RequestInit): Promise<Response> => {
		if (init?.method === "POST") {
			loginCount += 1;
			return Response.json({ access_token: `token-${loginCount}`, token_type: "bearer", expires_in: 60 });
		}
		headers.push(new Headers(init?.headers).get("authorization") || "");
		return Response.json([]);
	};
	const client = new NojoinClient({
		baseUrl: "https://nojoin.test",
		username: "private-user",
		password: "private-password",
		fetchImpl: fakeFetch as typeof fetch,
		now: () => now,
	});
	await client.listActiveRecordings();
	now = 31_000;
	await client.listActiveRecordings();
	assert.equal(loginCount, 2);
	assert.deepEqual(headers, ["Bearer token-1", "Bearer token-2"]);
});

test("recovers after a temporary Nojoin outage", async () => {
	let calls = 0;
	const fakeFetch = async (): Promise<Response> => {
		calls += 1;
		if (calls === 1) throw new Error("private network detail");
		return Response.json([]);
	};
	const client = new NojoinClient({
		baseUrl: "https://nojoin.test",
		token: "secret-token",
		fetchImpl: fakeFetch as typeof fetch,
	});
	await assert.rejects(() => client.listActiveRecordings(), /Nojoin is unreachable/);
	assert.deepEqual(await client.listActiveRecordings(), []);
});

test("includes meeting focus, brief, and source-aware transcript in adviser context", () => {
	const prompt = buildAdvicePrompt({
		mode: "automatic",
		focus: "Challenge timeline assumptions",
		brief: "GA4 cross-domain tracking is missing from the checkout domain.",
		rollingContext: "Migration owner is unknown.",
		recent: [utterance("u1", "Can we finish by Friday?")],
		newestIds: new Set(["u1"]),
		previousAdvice: [],
	});
	assert.match(prompt, /Challenge timeline assumptions/);
	assert.match(prompt, /GA4 cross-domain tracking is missing/);
	assert.match(ADVISER_SYSTEM_PROMPT, /first try to produce a direct SAY answer/);
	assert.match(ADVISER_SYSTEM_PROMPT, /Do not turn an answerable client question into another question/);
	assert.match(prompt, /LIKELY OTHERS \[system channel\]/);
	assert.match(prompt, /NEW/);
});

test("builds private context for direct chat questions", () => {
	const context = buildDirectChatContext({
		recordingName: "Client review",
		focus: "Make recommendations concrete",
		brief: "Retention is currently two months.",
		rollingContext: "The client asked what to fix first.",
		recent: [utterance("u1", "What would you prioritize?")],
	});
	assert.match(context, /Give the answer first/);
	assert.match(context, /Retention is currently two months/);
	assert.match(context, /LIKELY OTHERS \[system channel\]/);
	assert.match(context, /What would you prioritize\?/);
});
