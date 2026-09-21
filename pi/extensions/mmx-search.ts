import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

interface MmxSearchResult {
  title: string;
  link: string;
  snippet: string;
  date?: string;
}

interface MmxSearchResponse {
  organic?: MmxSearchResult[];
  base_resp?: { status_msg?: string; status_code?: number };
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "web_search_mmx",
    label: "Web Search",
    description:
      "Search the web via `mmx search query`. Returns titles, URLs, and snippets.",
    promptSnippet: "Search the web for current information",
    promptGuidelines: [
      "Use web_search_mmx when you need up-to-date info beyond your training cutoff, look up libraries/docs, verify facts, or find current news.",
    ],
    parameters: Type.Object({
      query: Type.String({ description: "Search query string" }),
    }),
    async execute(_toolCallId, params, signal) {
      const args = ["search", "query", "--q", params.query, "--output", "json"];

      try {
        const { stdout } = await execFileAsync("mmx", args, {
          maxBuffer: 10 * 1024 * 1024,
          signal,
        });
        const data = JSON.parse(stdout) as MmxSearchResponse;

        if (data.base_resp && data.base_resp.status_code !== 0) {
          return {
            content: [
              {
                type: "text",
                text: `mmx search error: ${data.base_resp.status_msg ?? "unknown"}`,
              },
            ],
            isError: true,
          };
        }

        const results = data.organic ?? [];
        if (results.length === 0) {
          return {
            content: [{ type: "text", text: `No results for "${params.query}".` }],
          };
        }

        const formatted = results
          .map((r, i) => {
            const date = r.date ? ` (${r.date})` : "";
            return `[${i + 1}] ${r.title}${date}\n${r.link}\n${r.snippet}`;
          })
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `${results.length} result(s) for "${params.query}":\n\n${formatted}`,
            },
          ],
        };
      } catch (err: unknown) {
        const e = err as { killed?: boolean; message?: string };
        if (e.killed || signal?.aborted) {
          return {
            content: [{ type: "text", text: "Search cancelled." }],
            isError: true,
          };
        }
        return {
          content: [
            { type: "text", text: `Search failed: ${e.message ?? String(err)}` },
          ],
          isError: true,
        };
      }
    },
  });

  pi.registerCommand("search", {
    description: "Search the web: /search <query>",
    handler: async (args, ctx) => {
      const query = args?.trim();
      if (!query) {
        ctx.ui.notify("Usage: /search <query>", "warn");
        return;
      }
      pi.sendUserMessage(
        `Use the web_search_mmx tool with query: "${query}"`,
      );
    },
  });
}
