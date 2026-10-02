import { homedir } from "node:os";
import { isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

interface ConversionResult {
	output: string;
	attachments: number;
	messages: number;
}

const CONVERTER = fileURLToPath(new URL("./convert.py", import.meta.url));

function resolveInput(raw: string, cwd: string): string {
	let value = raw.trim().replace(/^@/u, "");
	if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
		value = value.slice(1, -1);
	}
	if (value === "~") value = homedir();
	else if (value.startsWith("~/")) value = join(homedir(), value.slice(2));
	return isAbsolute(value) ? value : resolve(cwd, value);
}

function parseResult(stdout: string): ConversionResult {
	const value = JSON.parse(stdout) as Partial<ConversionResult>;
	if (typeof value.output !== "string" || typeof value.attachments !== "number" || typeof value.messages !== "number") {
		throw new Error("Converter returned an invalid result");
	}
	return value as ConversionResult;
}

function errorText(value: string): string {
	return value.trim().replace(/\s+/gu, " ").slice(0, 500) || "Email conversion failed";
}

export default function emlOrgExtension(pi: ExtensionAPI): void {
	pi.registerCommand("eml-org", {
		description: "Convert an EML file to ~/org/email with org-attach files",
		handler: async (args, ctx) => {
			if (!args.trim()) {
				ctx.ui.notify("Usage: /eml-org PATH.eml", "warning");
				return;
			}

			ctx.ui.setStatus("eml-org", "converting email…");
			try {
				const source = resolveInput(args, ctx.cwd);
				const result = await pi.exec("python3", [CONVERTER, source], { timeout: 120_000 });
				if (result.code !== 0) throw new Error(errorText(result.stderr));
				const converted = parseResult(result.stdout);
				ctx.ui.notify(
					`Created ${converted.output}\n${converted.messages} message(s), ${converted.attachments} attachment(s)`,
					"info",
				);
			} catch (error) {
				ctx.ui.notify(error instanceof Error ? error.message : "Email conversion failed", "error");
			} finally {
				ctx.ui.setStatus("eml-org", undefined);
			}
		},
	});
}
