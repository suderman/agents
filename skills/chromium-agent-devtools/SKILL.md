---
name: chromium-agent-devtools
description: Use Chrome DevTools MCP against the local Chromium launched by the chromium-agent binary. Use for browser automation, page inspection, screenshots, console/network checks, and debugging web apps in Pi without loading external/opencode skill directories.
license: CC0-1.0
---

# Chromium Agent DevTools

Use this skill when a task needs browser automation or inspection in Chromium from Pi.

## Browser target

Use the Chromium instance launched by:

```sh
chromium-agent
```

Do not launch raw `chromium`, `google-chrome`, Playwright, Puppeteer, or a fresh browser profile unless user explicitly asks or DevTools/CDP cannot do the job.

This setup expects Chrome DevTools Protocol on:

```text
http://127.0.0.1:9222
```

Pi MCP config should point `chrome-devtools` at that URL, e.g. `--browser-url=http://127.0.0.1:9222`.

## Startup check

Before blaming MCP, check whether `chromium-agent` is running and exposing CDP:

```sh
pgrep -af 'chromium.*remote-debugging|chromium-agent'
curl -sS --max-time 2 http://127.0.0.1:9222/json/version
```

If no target is reachable, start it:

```sh
chromium-agent
```

If the command would tie up the current shell, start it in the background:

```sh
nohup chromium-agent >/tmp/chromium-agent.log 2>&1 &
```

Then re-run the `curl` check.

## Control path order

1. Prefer Pi's direct `chrome_devtools_*` tools when available.
2. If direct tools are unavailable, use MCP gateway for the `chrome-devtools` server.
3. If MCP is disconnected, verify CDP with the startup check before changing MCP config.
4. If CDP works but MCP fails, reconnect/list MCP server tools before trying another browser stack.

## Minimum proof of browser control

A running process or visible window is not enough. Prove control with one real browser operation:

- list/select pages or targets
- read page title, URL, DOM text, console messages, or network requests
- navigate, click, type, evaluate script, or take screenshot

## Reporting rule

When reporting browser work, state which path was used:

- `chrome_devtools_*` direct tools
- `chrome-devtools` MCP through gateway
- direct CDP fallback
- no browser control available

Keep scope small. Do not build a new automation stack when DevTools MCP/CDP can inspect or control the existing `chromium-agent` browser.
