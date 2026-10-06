/**
 * Hyprland Desktop Automation
 *
 * First-pass Pi extension for recent Hyprland Lua dispatch syntax.
 * It intentionally exposes typed, narrow tools before raw dispatch/eval.
 */

import { StringEnum, Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

type ExecResult = Awaited<ReturnType<ExtensionAPI["exec"]>>;

type ToolResponse = {
	content: Array<{ type: "text"; text: string }>;
	details?: Record<string, unknown>;
};

const QUERY_COMMANDS = [
	"monitors",
	"workspaces",
	"clients",
	"activewindow",
	"layers",
	"devices",
	"instances",
	"layouts",
	"configerrors",
	"cursorpos",
	"locked",
	"descriptions",
	"submap",
] as const;

const ACTIONS = ["toggle", "set", "unset"] as const;
const FULLSCREEN_MODES = ["fullscreen", "maximized"] as const;
const DANGEROUS_EXPR_PATTERNS: Array<{ label: string; pattern: RegExp }> = [
	{ label: "exec_cmd/exec_raw", pattern: /\bexec_(cmd|raw)\s*\(/ },
	{ label: "window.kill", pattern: /\bwindow\.kill\s*\(/ },
	{ label: "window.signal", pattern: /\bwindow\.signal\s*\(/ },
	{ label: "exit", pattern: /\bexit\s*\(/ },
];

function textResponse(text: string, details?: Record<string, unknown>): ToolResponse {
	return {
		content: [{ type: "text", text }],
		details,
	};
}

function assertHyprlandEnv(): void {
	if (!process.env.HYPRLAND_INSTANCE_SIGNATURE) {
		throw new Error("HYPRLAND_INSTANCE_SIGNATURE is not set. Is this Pi process running inside Hyprland?");
	}
}

function luaString(value: string): string {
	if (value.length > 200) throw new Error("String argument too long for Hyprland Lua dispatch");
	if (/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)) {
		throw new Error("String argument contains unsupported control characters");
	}

	return `"${value
		.replace(/\\/g, "\\\\")
		.replace(/"/g, '\\"')
		.replace(/\n/g, "\\n")
		.replace(/\r/g, "\\r")
		.replace(/\t/g, "\\t")}"`;
}

function validateLuaExpr(expr: string): void {
	if (expr.length > 1000) throw new Error("Lua dispatch expression is too long");
	if (/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(expr)) {
		throw new Error("Lua dispatch expression contains unsupported control characters");
	}
	if (!expr.includes("hl.dsp.")) {
		throw new Error("Raw dispatch must call an hl.dsp.* dispatcher expression");
	}
}

function dangerousExprLabels(expr: string): string[] {
	return DANGEROUS_EXPR_PATTERNS.filter((entry) => entry.pattern.test(expr)).map((entry) => entry.label);
}

async function execHyprctl(
	pi: ExtensionAPI,
	args: string[],
	signal?: AbortSignal,
	options: { requireHyprland?: boolean } = { requireHyprland: true },
): Promise<ExecResult> {
	if (options.requireHyprland !== false) assertHyprlandEnv();

	const result = await pi.exec("hyprctl", args, { signal, timeout: 5000 });
	if (result.code !== 0) {
		const message = [result.stderr, result.stdout].filter(Boolean).join("\n").trim();
		throw new Error(message || `hyprctl ${args.join(" ")} failed with exit code ${result.code}`);
	}
	return result;
}

async function dispatchLua(pi: ExtensionAPI, expr: string, signal?: AbortSignal): Promise<string> {
	validateLuaExpr(expr);
	const result = await execHyprctl(pi, ["dispatch", expr], signal);
	return result.stdout.trim() || "ok";
}

export default function (pi: ExtensionAPI) {
	pi.registerTool({
		name: "hyprland_status",
		label: "Hyprland Status",
		description: "Check whether Hyprland automation is available and report hyprctl version/config errors.",
		promptSnippet: "Check Hyprland automation availability and current config errors",
		promptGuidelines: [
			"Use hyprland_status before desktop automation if Hyprland availability is uncertain.",
		],
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, signal) {
			const signature = process.env.HYPRLAND_INSTANCE_SIGNATURE || "";
			const runtimeDir = process.env.XDG_RUNTIME_DIR || "";
			const lines = [
				`HYPRLAND_INSTANCE_SIGNATURE=${signature || "<unset>"}`,
				`XDG_RUNTIME_DIR=${runtimeDir || "<unset>"}`,
			];

			try {
				const version = await execHyprctl(pi, ["version"], signal, { requireHyprland: false });
				lines.push("", version.stdout.trim());
			} catch (error) {
				lines.push("", `hyprctl version failed: ${error instanceof Error ? error.message : String(error)}`);
			}

			if (signature) {
				try {
					const configErrors = await execHyprctl(pi, ["configerrors"], signal);
					const output = configErrors.stdout.trim();
					lines.push("", output ? `Config errors:\n${output}` : "Config errors: none");
				} catch (error) {
					lines.push("", `hyprctl configerrors failed: ${error instanceof Error ? error.message : String(error)}`);
				}
			}

			return textResponse(lines.join("\n"), { hyprlandInstanceSignatureSet: Boolean(signature), runtimeDir });
		},
	});

	pi.registerTool({
		name: "hyprland_query",
		label: "Hyprland Query",
		description: "Query Hyprland state with `hyprctl -j`. Output is JSON for supported commands.",
		promptSnippet: "Query Hyprland monitors, workspaces, clients, active window, devices, and config errors",
		promptGuidelines: [
			"Use hyprland_query to inspect desktop state before choosing a Hyprland action.",
		],
		parameters: Type.Object({
			kind: StringEnum(QUERY_COMMANDS),
		}),
		async execute(_toolCallId, params, signal) {
			const result = await execHyprctl(pi, ["-j", params.kind], signal);
			return textResponse(result.stdout.trim() || "{}", { kind: params.kind });
		},
	});

	pi.registerTool({
		name: "hyprland_focus_workspace",
		label: "Hyprland Focus Workspace",
		description: "Switch focus to a Hyprland workspace using recent Lua dispatch syntax.",
		promptSnippet: "Switch Hyprland focus to a workspace",
		promptGuidelines: [
			"Use hyprland_focus_workspace instead of legacy `hyprctl dispatch workspace ...` commands.",
		],
		parameters: Type.Object({
			workspace: Type.String({ description: "Workspace selector, e.g. 1, name:web, special:magic, r+1" }),
			onCurrentMonitor: Type.Optional(Type.Boolean({ description: "Keep workspace on current monitor when supported" })),
		}),
		async execute(_toolCallId, params, signal) {
			const expr = `hl.dsp.focus({ workspace = ${luaString(params.workspace)}${params.onCurrentMonitor === undefined ? "" : `, on_current_monitor = ${params.onCurrentMonitor ? "true" : "false"}`} })`;
			const output = await dispatchLua(pi, expr, signal);
			return textResponse(output, { expr, workspace: params.workspace, onCurrentMonitor: params.onCurrentMonitor });
		},
	});

	pi.registerTool({
		name: "hyprland_focus_direction",
		label: "Hyprland Focus Direction",
		description: "Move focus in a direction using recent Lua dispatch syntax.",
		promptSnippet: "Move Hyprland focus left, right, up, or down",
		parameters: Type.Object({
			direction: StringEnum(["l", "r", "u", "d", "left", "right", "up", "down"] as const),
		}),
		async execute(_toolCallId, params, signal) {
			const directionMap: Record<string, string> = { left: "l", right: "r", up: "u", down: "d" };
			const direction = directionMap[params.direction] ?? params.direction;
			const expr = `hl.dsp.focus({ direction = ${luaString(direction)} })`;
			const output = await dispatchLua(pi, expr, signal);
			return textResponse(output, { expr, direction });
		},
	});

	pi.registerTool({
		name: "hyprland_focus_window",
		label: "Hyprland Focus Window",
		description: "Focus a Hyprland window by selector using recent Lua dispatch syntax.",
		promptSnippet: "Focus a Hyprland window by selector",
		parameters: Type.Object({
			window: Type.String({ description: "Window selector, e.g. class:firefox, title:Notes, address:0x..., activewindow" }),
		}),
		async execute(_toolCallId, params, signal) {
			const expr = `hl.dsp.focus({ window = ${luaString(params.window)} })`;
			const output = await dispatchLua(pi, expr, signal);
			return textResponse(output, { expr, window: params.window });
		},
	});

	pi.registerTool({
		name: "hyprland_move_window_to_workspace",
		label: "Hyprland Move Window",
		description: "Move active or selected window to a workspace using recent Lua dispatch syntax.",
		promptSnippet: "Move a Hyprland window to a workspace",
		promptGuidelines: [
			"Use hyprland_move_window_to_workspace instead of legacy `movetoworkspace` commands.",
		],
		parameters: Type.Object({
			workspace: Type.String({ description: "Workspace selector, e.g. 1, name:web, special:magic" }),
			follow: Type.Optional(Type.Boolean({ description: "Also follow focus to that workspace" })),
			window: Type.Optional(Type.String({ description: "Optional window selector. Omit for active window." })),
		}),
		async execute(_toolCallId, params, signal) {
			const expr = `hl.dsp.window.move({ workspace = ${luaString(params.workspace)}${params.follow === undefined ? "" : `, follow = ${params.follow ? "true" : "false"}`}${params.window ? `, window = ${luaString(params.window)}` : ""} })`;
			const output = await dispatchLua(pi, expr, signal);
			return textResponse(output, { expr, workspace: params.workspace, follow: params.follow, window: params.window });
		},
	});

	pi.registerTool({
		name: "hyprland_window_state",
		label: "Hyprland Window State",
		description: "Change active or selected window state: float, fullscreen, pseudo, or close.",
		promptSnippet: "Toggle float/fullscreen/pseudo or close Hyprland windows",
		promptGuidelines: [
			"Use hyprland_window_state for common active-window actions instead of raw Lua dispatch.",
			"Do not close windows with hyprland_window_state unless the user asked to close a window.",
		],
		parameters: Type.Object({
			operation: StringEnum(["float", "fullscreen", "pseudo", "close"] as const),
			action: Type.Optional(StringEnum(ACTIONS)),
			mode: Type.Optional(StringEnum(FULLSCREEN_MODES)),
			window: Type.Optional(Type.String({ description: "Optional Hyprland window selector. Omit for active window." })),
		}),
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			if (params.operation === "close") {
				if (!ctx.hasUI) throw new Error("Refusing to close a window without UI confirmation");
				const ok = await ctx.ui.confirm("Close Hyprland window?", params.window ? `Close window selector: ${params.window}` : "Close active window?");
				if (!ok) throw new Error("Window close cancelled by user");
			}

			const windowPart = params.window ? `, window = ${luaString(params.window)}` : "";
			let expr: string;
			if (params.operation === "fullscreen") {
				expr = `hl.dsp.window.fullscreen({ action = ${luaString(params.action ?? "toggle")}, mode = ${luaString(params.mode ?? "fullscreen")}${windowPart} })`;
			} else if (params.operation === "float") {
				expr = `hl.dsp.window.float({ action = ${luaString(params.action ?? "toggle")}${windowPart} })`;
			} else if (params.operation === "pseudo") {
				expr = `hl.dsp.window.pseudo({ action = ${luaString(params.action ?? "toggle")}${windowPart} })`;
			} else {
				expr = params.window ? `hl.dsp.window.close(${luaString(params.window)})` : "hl.dsp.window.close()";
			}

			const output = await dispatchLua(pi, expr, signal);
			return textResponse(output, { expr, operation: params.operation, action: params.action, mode: params.mode, window: params.window });
		},
	});

	pi.registerTool({
		name: "hyprland_reload",
		label: "Hyprland Reload",
		description: "Reload Hyprland config, then report config errors.",
		promptSnippet: "Reload Hyprland config and check config errors",
		parameters: Type.Object({}),
		async execute(_toolCallId, _params, signal) {
			const reload = await execHyprctl(pi, ["reload"], signal);
			const configErrors = await execHyprctl(pi, ["configerrors"], signal);
			const reloadText = reload.stdout.trim() || "reload requested";
			const errorsText = configErrors.stdout.trim() || "Config errors: none";
			return textResponse(`${reloadText}\n\n${errorsText}`, { reloaded: true });
		},
	});

	pi.registerTool({
		name: "hyprland_dispatch_lua",
		label: "Hyprland Lua Dispatch",
		description: "Advanced escape hatch: run `hyprctl dispatch '<hl.dsp.* expression>'`. Prefer typed hyprland_* tools. Dangerous expressions require confirmation.",
		promptSnippet: "Run a recent Hyprland Lua dispatcher expression when typed tools do not cover the needed action",
		promptGuidelines: [
			"Use hyprland_dispatch_lua only when no typed hyprland_* tool covers the requested action.",
			"hyprland_dispatch_lua expects recent Lua syntax like `hl.dsp.focus({ workspace = \"3\" })`, not legacy dispatcher arguments.",
		],
		parameters: Type.Object({
			expr: Type.String({ description: "Lua dispatcher expression, e.g. hl.dsp.focus({ workspace = \"3\" })" }),
		}),
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			validateLuaExpr(params.expr);
			const dangerous = dangerousExprLabels(params.expr);
			if (dangerous.length > 0) {
				if (!ctx.hasUI) throw new Error(`Refusing dangerous Hyprland dispatch without UI confirmation: ${dangerous.join(", ")}`);
				const ok = await ctx.ui.confirm(
					`Dangerous Hyprland dispatch (${dangerous.join(", ")})`,
					`${params.expr}\n\nAllow?`,
				);
				if (!ok) throw new Error("Hyprland dispatch cancelled by user");
			}

			const output = await dispatchLua(pi, params.expr, signal);
			return textResponse(output, { expr: params.expr, dangerous });
		},
	});
}
