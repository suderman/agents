import type { ExtensionContext } from "@earendil-works/pi-coding-agent";
import { wrapTextWithAnsi } from "@earendil-works/pi-tui";

import type { Advice } from "./state.ts";

export type WidgetMode = "idle" | "listening" | "thinking" | "degraded" | "auth";

export interface WidgetState {
	enabled: boolean;
	mode: WidgetMode;
	advice?: Advice;
	history?: Advice[];
	message?: string;
}

export function updateWidget(ctx: ExtensionContext, state: WidgetState): void {
	if (!state.enabled) {
		ctx.ui.setWidget("nojoin", undefined);
		ctx.ui.setStatus("nojoin", undefined);
		return;
	}

	ctx.ui.setStatus(
		"nojoin",
		ctx.ui.theme.fg(state.mode === "degraded" || state.mode === "auth" ? "warning" : "accent", "nojoin"),
	);
	ctx.ui.setWidget("nojoin", (_tui, theme) => ({
		invalidate() {},
		render(width: number): string[] {
			const boxWidth = Math.max(16, Math.min(width, 76));
			const title = " LIVE ADVISER ";
			const top = `┌─${title}${"─".repeat(Math.max(0, boxWidth - title.length - 2))}`.slice(0, boxWidth);
			const bottom = `└${"─".repeat(Math.max(0, boxWidth - 1))}`;
			const contentWidth = Math.max(1, boxWidth - 4);
			const advice = state.advice;
			const history = (state.history?.length ? state.history : advice ? [advice] : []).slice(-5);

			if (history.length > 0) {
				const lines = [theme.fg("borderAccent", top)];
				for (const item of history) {
					const color = item.priority === "high" ? "warning" : "accent";
					const label = theme.fg(color, theme.bold(item.action.toUpperCase()));
					const time = new Date(item.shownAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
					if (lines.length > 1) lines.push("│");
					lines.push(`│ ${theme.fg("dim", time)} ${label}`);
					lines.push(...wrapTextWithAnsi(item.text, contentWidth).map((line) => `│ ${theme.fg("text", line)}`));
				}
				if (state.mode === "thinking") lines.push(`│ ${theme.fg("dim", "Thinking…")}`);
				else if (state.message) lines.push(`│ ${theme.fg("dim", state.message)}`);
				lines.push(theme.fg("borderAccent", bottom));
				return lines;
			}

			const quiet =
				state.mode === "auth"
					? "Authentication needed"
					: state.mode === "degraded"
						? "Nojoin unavailable · retrying"
						: state.mode === "idle"
							? "Waiting for a live meeting…"
							: state.mode === "thinking"
								? "Thinking…"
								: state.message || "Listening… · Ctrl+Alt+H for help";
			return [theme.fg("borderMuted", top), `│ ${theme.fg("dim", quiet)}`, theme.fg("borderMuted", bottom)];
		},
	}));
}

export function formatTime(value?: number): string {
	return value ? new Date(value).toLocaleTimeString() : "never";
}
