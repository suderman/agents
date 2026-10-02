import { StringEnum } from "@earendil-works/pi-ai";
import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import { buildAdvicePrompt, buildSummaryPrompt, ADVISER_SYSTEM_PROMPT, type AdvicePromptInput } from "./prompt.ts";
import { parseAdvicePayload, parseAdviceText, type AdvicePayload, type Utterance } from "./state.ts";

const ADVICE_TOOL = {
	name: "submit_advice",
	description: "Return the single live-adviser decision for the current meeting moment.",
	parameters: Type.Object(
		{
			action: StringEnum(["silent", "say", "ask", "watch"] as const),
			text: Type.String({ maxLength: 240 }),
			priority: StringEnum(["normal", "high"] as const),
			reason: Type.String({ maxLength: 500 }),
		},
		{ additionalProperties: false },
	),
	constrainedSampling: { type: "json_schema" as const, strict: "prefer" as const },
};

export interface ResolvedModel {
	model: NonNullable<ExtensionContext["model"]>;
	name: string;
}

export function resolveAdviserModel(ctx: ExtensionContext, configured?: string): ResolvedModel | undefined {
	const available = ctx.modelRegistry.getAvailable();
	const wanted = configured?.trim();
	if (wanted) {
		const separator = wanted.indexOf("/");
		const match =
			separator > 0
				? available.find(
						(model) => model.provider === wanted.slice(0, separator) && model.id === wanted.slice(separator + 1),
					)
				: available.find((model) => model.id === wanted);
		if (match) return { model: match, name: `${match.provider}/${match.id}` };
	}

	const preferredProvider = ctx.model?.provider;
	const luna =
		available.find((model) => model.provider === preferredProvider && model.id === "gpt-5.6-luna") ??
		available.find((model) => model.provider === "codex-lb" && model.id === "gpt-5.6-luna") ??
		available.find((model) => model.id === "gpt-5.6-luna") ??
		available.find((model) => model.id.endsWith("/gpt-5.6-luna"));
	if (luna) return { model: luna, name: `${luna.provider}/${luna.id}` };
	if (ctx.model && available.some((model) => model.provider === ctx.model?.provider && model.id === ctx.model?.id)) {
		return { model: ctx.model, name: `${ctx.model.provider}/${ctx.model.id}` };
	}
	const fallback = available[0];
	return fallback ? { model: fallback, name: `${fallback.provider}/${fallback.id}` } : undefined;
}

function responseText(response: Awaited<ReturnType<ExtensionContext["modelRegistry"]["complete"]>>): string {
	return response.content
		.filter((content): content is { type: "text"; text: string } => content.type === "text")
		.map((content) => content.text)
		.join("\n");
}

function responseAdvice(response: Awaited<ReturnType<ExtensionContext["modelRegistry"]["complete"]>>): AdvicePayload | undefined {
	const call = response.content.find((content) => content.type === "toolCall" && content.name === ADVICE_TOOL.name);
	if (call?.type === "toolCall") return parseAdvicePayload(call.arguments);
	return parseAdviceText(responseText(response));
}

function modelError(
	label: string,
	response: Awaited<ReturnType<ExtensionContext["modelRegistry"]["complete"]>>,
): Error {
	const detail = response.errorMessage?.trim().replace(/\s+/gu, " ").slice(0, 300);
	return new Error(detail ? `${label}: ${detail}` : `${label} failed`);
}

export async function requestAdvice(
	ctx: ExtensionContext,
	resolved: ResolvedModel,
	input: AdvicePromptInput,
	signal: AbortSignal,
	sessionId: string,
): Promise<AdvicePayload> {
	const prompt = buildAdvicePrompt(input);
	for (let attempt = 0; attempt < 2; attempt += 1) {
		const response = await ctx.modelRegistry.complete(
			resolved.model,
			{
				systemPrompt: ADVISER_SYSTEM_PROMPT,
				messages: [
					{
						role: "user",
						content: [
							{
								type: "text",
								text:
									attempt === 0
										? prompt
										: `${prompt}\n\nYour prior output was malformed. Call submit_advice once with all required fields.`,
							},
						],
						timestamp: Date.now(),
					},
				],
				tools: [ADVICE_TOOL],
			},
			{
				signal,
				reasoning: "minimal",
				toolChoice: "required",
				maxTokens: 300,
				cacheRetention: "short",
				sessionId,
			},
		);
		if (response.stopReason === "aborted") throw new Error("Adviser inference aborted");
		if (response.stopReason === "error") throw modelError("Adviser model request failed", response);
		const parsed = responseAdvice(response);
		if (parsed) return parsed;
	}
	return { action: "silent", text: "", priority: "normal", reason: "Malformed model output" };
}

export async function requestRollingContext(
	ctx: ExtensionContext,
	resolved: ResolvedModel,
	rollingContext: string,
	focus: string,
	recent: Utterance[],
	signal: AbortSignal,
	sessionId: string,
): Promise<string> {
	const response = await ctx.modelRegistry.complete(
		resolved.model,
		{
			systemPrompt: "You maintain terse, factual meeting context. Do not give advice and do not invent details.",
			messages: [
				{
					role: "user",
					content: [{ type: "text", text: buildSummaryPrompt(rollingContext, focus, recent) }],
					timestamp: Date.now(),
				},
			],
		},
		{
			signal,
			reasoning: "minimal",
			maxTokens: 500,
			cacheRetention: "short",
			sessionId: `${sessionId}-context`,
		},
	);
	if (response.stopReason === "aborted") throw new Error("Context update aborted");
	if (response.stopReason === "error") throw modelError("Context model request failed", response);
	return responseText(response).trim().slice(0, 3_000) || rollingContext;
}
