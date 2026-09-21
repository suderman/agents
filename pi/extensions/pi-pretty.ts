/**
 * Compact, responsive Pi statusline with fullscreen mouse actions.
 *
 * Keeps the visual treatment local and dependency-free while borrowing the
 * colored Powerline rhythm and priority-based fitting of pi-statusline.
 */

import type {
	ExtensionAPI,
	ExtensionContext,
	Theme,
	ThemeColor,
} from "@earendil-works/pi-coding-agent";
import {
	Key,
	Text,
	matchesKey,
	truncateToWidth,
	type TuiMouseEvent,
	type TuiMouseEventResult,
	visibleWidth,
} from "@earendil-works/pi-tui";
import { homedir } from "node:os";
import { basename } from "node:path";

type ThinkingLevel =
	| "off"
	| "minimal"
	| "low"
	| "medium"
	| "high"
	| "xhigh"
	| "max";

type SegmentId = "model" | "cwd" | "branch" | "status" | "context";

type Segment = {
	id: SegmentId;
	icon: string;
	text: string;
	background: ThemeColor;
	foreground: ThemeColor;
	priority: number;
	clickable?: boolean;
};

type ClickRange = {
	id: SegmentId;
	start: number;
	end: number;
};

const HOME = homedir();
const POWERLINE_END = "";
const THINKING_LEVELS: ThinkingLevel[] = [
	"off",
	"minimal",
	"low",
	"medium",
	"high",
	"xhigh",
	"max",
];
const THINKING_COLORS = {
	off: "thinkingOff",
	minimal: "thinkingMinimal",
	low: "thinkingLow",
	medium: "thinkingMedium",
	high: "thinkingHigh",
	xhigh: "thinkingXhigh",
	max: "thinkingMax",
} satisfies Record<ThinkingLevel, ThemeColor>;

function formatCount(count: number): string {
	if (count < 1000) return count.toString();
	if (count < 10_000) return `${(count / 1000).toFixed(1)}k`;
	if (count < 1_000_000) return `${Math.round(count / 1000)}k`;
	if (count < 10_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
	return `${Math.round(count / 1_000_000)}M`;
}

function projectName(cwd: string): string {
	if (cwd === HOME) return "~";
	return basename(cwd) || cwd;
}

function thinkingLevel(pi: ExtensionAPI): ThinkingLevel {
	const level = pi.getThinkingLevel();
	return THINKING_LEVELS.includes(level as ThinkingLevel)
		? (level as ThinkingLevel)
		: "off";
}

function modelSlug(ctx: ExtensionContext): string {
	return ctx.model?.id || "no-model";
}

function contextSegment(ctx: ExtensionContext): Segment | undefined {
	const usage = ctx.getContextUsage();
	if (!usage?.contextWindow) return undefined;

	const percent = usage.percent;
	let color: ThemeColor = "borderAccent";
	if (percent !== null && percent >= 90) color = "error";
	else if (percent !== null && percent >= 70) color = "warning";
	const value =
		percent === null
			? `ctx ?/${formatCount(usage.contextWindow)}`
			: `ctx ${percent.toFixed(1)}%/${formatCount(usage.contextWindow)}`;

	return {
		id: "context",
		icon: "󰍛",
		text: value,
		background: "selectedBg",
		foreground: color,
		priority: 95,
		clickable: true,
	};
}

function compactStatus(value: string): string | undefined {
	const text = value
		.replace(/\x1b\[[0-9;]*m/g, "")
		.replace(
			/(?:\p{Regional_Indicator}+|[#*0-9]\uFE0F?\u20E3|\p{Extended_Pictographic}(?:\uFE0F|\p{Emoji_Modifier})?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\p{Emoji_Modifier})?)*|\p{Emoji_Modifier})/gu,
			"",
		)
		.trim();
	if (!text || text.startsWith("DCP:")) return undefined;

	const mcp = text.match(/^MCP:\s*(\d+) servers? enabled\b/i);
	if (mcp) {
		const enabled = Number(mcp[1]);
		const disabled = Number(text.match(/\((\d+) disabled\)/i)?.[1] || 0);
		return `MCP: ${enabled}/${enabled + disabled}`;
	}

	return text
		.replace(/^MCP\s+(\d+\/\d+)$/i, "MCP: $1")
		.replace(/LSP Active:\s*/g, "LSP: ")
		.replace(/LSP Failed:\s*/g, "LSP failed: ")
		.replace(/LSP Inactive/g, "LSP: inactive");
}

function extensionStatusSegment(statuses: ReadonlyMap<string, string>): Segment | undefined {
	const values = Array.from(statuses.values()).flatMap((value) => {
		const compact = compactStatus(value);
		return compact ? [compact] : [];
	});
	if (values.length === 0) return undefined;
	return {
		id: "status",
		icon: "",
		text: values.join(" · "),
		background: "toolPendingBg",
		foreground: "muted",
		priority: 55,
	};
}

function renderBrand(theme: Theme): string {
	return (
		theme.fg("dim", "░") +
		theme.fg("muted", "▒") +
		theme.fg("accent", "▓")
	);
}

function capColor(theme: Theme, background: Segment["background"]): string {
	// Pi keeps background tokens out of fg(); the SGR color has the same value
	// with 38 (foreground) in place of 48 (background).
	return theme.getBgAnsi(background).replace("\x1b[48;", "\x1b[38;");
}

function renderSegments(
	theme: Theme,
	segments: Segment[],
	hovered: SegmentId | undefined,
	showBrand: boolean,
): { text: string; ranges: ClickRange[] } {
	let text = showBrand ? renderBrand(theme) : "";
	let column = visibleWidth(text);
	const ranges: ClickRange[] = [];

	segments.forEach((segment, index) => {
		const label = ` ${segment.icon} ${segment.text} `;
		const styledLabel = hovered === segment.id ? theme.bold(label) : label;
		const body = theme.bg(
			segment.background,
			theme.fg(segment.foreground, styledLabel),
		);
		const start = column;
		text += body;
		column += visibleWidth(body);
		const clickRange = segment.clickable
			? { id: segment.id, start, end: column }
			: undefined;
		if (clickRange) ranges.push(clickRange);

		const next = segments[index + 1];
		if (!next || next.background !== segment.background) {
			const cap = `${capColor(theme, segment.background)}${POWERLINE_END}\x1b[39m`;
			const separator = next ? theme.bg(next.background, cap) : cap;
			text += separator;
			column += visibleWidth(separator);
			if (clickRange) clickRange.end = column;
		}
	});

	return { text, ranges };
}

function fitSegments(
	theme: Theme,
	allSegments: Segment[],
	hovered: SegmentId | undefined,
	width: number,
): { text: string; ranges: ClickRange[] } {
	let segments = [...allSegments];
	let showBrand = true;
	let rendered = renderSegments(theme, segments, hovered, showBrand);

	if (visibleWidth(rendered.text) > width) {
		showBrand = false;
		rendered = renderSegments(theme, segments, hovered, showBrand);
	}

	while (visibleWidth(rendered.text) > width && segments.length > 1) {
		const lowest = Math.min(...segments.map((segment) => segment.priority));
		const dropIndex = segments.findLastIndex((segment) => segment.priority === lowest);
		segments.splice(dropIndex, 1);
		rendered = renderSegments(theme, segments, hovered, showBrand);
	}

	if (visibleWidth(rendered.text) <= width) return rendered;

	const text = truncateToWidth(rendered.text, width, "");
	const renderedWidth = visibleWidth(text);
	return {
		text,
		ranges: rendered.ranges.flatMap((range) =>
			range.start < renderedWidth
				? [{ ...range, end: Math.min(range.end, renderedWidth) }]
				: [],
		),
	};
}

async function chooseModel(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	if (!ctx.isIdle()) {
		ctx.ui.notify("Wait for current response before changing model", "info");
		return;
	}

	const candidates =
		ctx.scopedModels.length > 0
			? ctx.scopedModels.map(({ model, thinkingLevel }) => ({ model, thinkingLevel }))
			: ctx.modelRegistry.getAvailable().map((model) => ({ model, thinkingLevel: undefined }));
	const choices = candidates.map(({ model }) => {
		const active = model.provider === ctx.model?.provider && model.id === ctx.model?.id;
		return `${active ? "●" : "○"} ${model.name || model.id} · ${model.provider}/${model.id}`;
	});
	const selected = await ctx.ui.select("Choose model", choices);
	if (!selected) return;

	const candidate = candidates[choices.indexOf(selected)];
	if (!candidate) return;
	if (!(await pi.setModel(candidate.model))) {
		ctx.ui.notify(`No credentials for ${candidate.model.provider}`, "error");
		return;
	}
	if (candidate.thinkingLevel) {
		pi.setThinkingLevel(candidate.thinkingLevel as ThinkingLevel);
	}
}

async function chooseThinking(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	if (!ctx.isIdle()) {
		ctx.ui.notify("Wait for current response before changing thinking effort", "info");
		return;
	}

	const current = thinkingLevel(pi);
	const choices = THINKING_LEVELS.map(
		(level) => `${level === current ? "●" : "○"} ${level}`,
	);
	const selected = await ctx.ui.select("Thinking effort", choices);
	if (!selected) return;
	const selectedLevel = THINKING_LEVELS[choices.indexOf(selected)];
	if (selectedLevel) pi.setThinkingLevel(selectedLevel);
}

async function showDetails(
	pi: ExtensionAPI,
	ctx: ExtensionContext,
	branch: string | null,
): Promise<void> {
	const usage = ctx.getContextUsage();
	const sessionName = pi.getSessionName();
	let context = "unknown";
	if (usage?.contextWindow) {
		const tokens = usage.tokens === null ? "?" : formatCount(usage.tokens);
		const percent = usage.percent === null ? "" : ` (${usage.percent.toFixed(1)}%)`;
		context = `${tokens} / ${formatCount(usage.contextWindow)}${percent}`;
	}
	const rows = [
		["Model", ctx.model?.id || "none"],
		["Provider", ctx.model?.provider || "none"],
		["Thinking", thinkingLevel(pi)],
		["Context", context],
		["Directory", ctx.cwd],
		["Branch", branch || "none"],
		["Session", sessionName || "unnamed"],
	];

	await ctx.ui.custom<void>(
		(_tui, theme, _keybindings, done) => {
			const labelWidth = Math.max(...rows.map(([label]) => label.length));
			const content = [
				theme.fg("accent", theme.bold("Pi session")),
				"",
				...rows.map(
					([label, value]) =>
						`${theme.fg("muted", label.padEnd(labelWidth))}  ${theme.fg("text", value)}`,
				),
				"",
				theme.fg("dim", "Enter, Esc, or click to close"),
			].join("\n");
			const text = new Text(content, 1, 1, (line) =>
				theme.bg("customMessageBg", line),
			);
			return {
				render: (width) => text.render(width),
				invalidate: () => text.invalidate(),
				handleInput: (data: string) => {
					if (matchesKey(data, Key.escape) || matchesKey(data, Key.enter)) done();
				},
				handleMouse: (event: TuiMouseEvent): TuiMouseEventResult | undefined => {
					if (event.type !== "click" || event.button !== "left") return undefined;
					done();
					return { handled: true };
				},
			};
		},
		{
			overlay: true,
			overlayOptions: {
				anchor: "center",
				width: "65%",
				minWidth: 44,
				maxHeight: "80%",
			},
		},
	);
}

let requestFooterRender: (() => void) | undefined;

function installFooter(
	pi: ExtensionAPI,
	ctx: ExtensionContext,
	openMenu: (task: () => Promise<void>) => void,
): void {
	if (!ctx.hasUI) return;

	ctx.ui.setFooter((tui, theme, footerData) => {
		const requestRender = () => tui.requestRender();
		requestFooterRender = requestRender;
		const unsubscribe = footerData.onBranchChange(requestRender);
		let ranges: ClickRange[] = [];
		let hovered: SegmentId | undefined;

		const actionFor = (id: SegmentId): (() => Promise<void>) | undefined => {
			if (id === "model") return () => chooseModel(pi, ctx);
			if (id === "context")
				return () => showDetails(pi, ctx, footerData.getGitBranch());
			return undefined;
		};

		return {
			dispose(): void {
				unsubscribe();
				if (requestFooterRender === requestRender) requestFooterRender = undefined;
			},
			invalidate(): void {
				hovered = undefined;
			},
			render(width: number): string[] {
				const level = thinkingLevel(pi);
				const segments: Segment[] = [
					{
						id: "model",
						icon: "",
						text: `${modelSlug(ctx)}:${level}`,
						background: "selectedBg",
						foreground: THINKING_COLORS[level],
						priority: 100,
						clickable: true,
					},
					{
						id: "cwd",
						icon: "",
						text: projectName(ctx.cwd),
						background: "customMessageBg",
						foreground: "text",
						priority: 70,
					},
				];

				const branch = footerData.getGitBranch();
				if (branch) {
					segments.push({
						id: "branch",
						icon: "",
						text: branch,
						background: "toolSuccessBg",
						foreground: "success",
						priority: 80,
					});
				}

				const status = extensionStatusSegment(footerData.getExtensionStatuses());
				if (status) segments.push(status);
				const context = contextSegment(ctx);
				if (context) segments.push(context);

				const fitted = fitSegments(theme, segments, hovered, width);
				ranges = fitted.ranges;
				return [fitted.text];
			},
			handleMouse(event: TuiMouseEvent): TuiMouseEventResult | undefined {
				if (event.y !== 0) return undefined;
				const hit = ranges.find(
					(range) => event.x >= range.start && event.x < range.end,
				);

				if (event.type === "move") {
					const next = hit?.id;
					if (next === hovered) return next ? { handled: true } : undefined;
					hovered = next;
					return { handled: Boolean(next), render: true };
				}

				if (event.type !== "click" || event.button !== "left" || !hit) {
					return undefined;
				}
				const action = actionFor(hit.id);
				if (!action) return undefined;
				openMenu(action);
				return { handled: true };
			},
		};
	});
}

function installWorkingIndicator(ctx: ExtensionContext): void {
	if (!ctx.hasUI) return;
	const theme = ctx.ui.theme;
	ctx.ui.setWorkingIndicator({
		frames: [
			theme.fg("dim", "·"),
			theme.fg("muted", "•"),
			theme.fg("accent", "●"),
			theme.fg("borderAccent", "●"),
			theme.fg("mdListBullet", "●"),
			theme.fg("muted", "•"),
		],
		intervalMs: 110,
	});
}

export default function piPretty(pi: ExtensionAPI): void {
	let menuOpen = false;
	const openMenu = (task: () => Promise<void>): void => {
		if (menuOpen) return;
		menuOpen = true;
		void task().finally(() => {
			menuOpen = false;
			requestFooterRender?.();
		});
	};

	pi.registerCommand("pretty", {
		description: "Open statusline controls",
		handler: async (_args, ctx) => {
			if (menuOpen) return;
			const choice = await ctx.ui.select("Pi statusline", [
				"Choose model",
				"Choose thinking effort",
				"Show session details",
			]);
			if (choice === "Choose model") openMenu(() => chooseModel(pi, ctx));
			if (choice === "Choose thinking effort")
				openMenu(() => chooseThinking(pi, ctx));
			if (choice === "Show session details")
				openMenu(() => showDetails(pi, ctx, null));
		},
	});

	pi.on("session_start", async (_event, ctx) => {
		installWorkingIndicator(ctx);
		installFooter(pi, ctx, openMenu);
	});

	pi.on("context", async () => requestFooterRender?.());
	pi.on("turn_end", async () => requestFooterRender?.());
	pi.on("session_compact", async () => requestFooterRender?.());
	pi.on("model_select", async () => requestFooterRender?.());
	pi.on("thinking_level_select", async () => requestFooterRender?.());

	pi.on("session_shutdown", async (_event, ctx) => {
		requestFooterRender = undefined;
		menuOpen = false;
		if (!ctx.hasUI) return;
		ctx.ui.setFooter(undefined);
		ctx.ui.setWorkingIndicator();
	});
}
