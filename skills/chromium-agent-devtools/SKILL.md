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

Load `browser-control-basics` first. Its endpoint-selection rules also apply
when these tools are missing and direct CDP is used.

## Startup check

Resolve the browser for the current context:

```sh
if [ -n "${HERDR_WORKSPACE_ID:-}" ] && command -v herdr-hypr >/dev/null; then
  endpoint=$(herdr-hypr cdp --start) || exit 1
else
  endpoint=http://127.0.0.1:9222
fi
curl -fsS --max-time 2 "$endpoint/json/version"
```

Inside the pairing trial, each Herdr workspace has its own class, profile, and
dynamic CDP port. The helper starts only the caller's browser when needed.
Never use another workspace's port file or fall back to global 9222 after an
owned-endpoint failure. `chromium-agent --help` does not launch a browser.

Pi uses `herdr-hypr devtools --no-usage-statistics` in the trial. This launcher
starts or reuses the owned browser before connecting MCP. Outside Herdr it keeps
the global 9222 endpoint. If tools are unavailable, reconnect through `/mcp` or
use direct CDP against the resolved `$endpoint`. Reconnect after moving an
existing Pi pane to a different Herdr workspace.

On hosts without the trial, retain the global browser on 9222. If it is absent,
start `chromium-agent` in the background and repeat the endpoint check.

## Control path order

1. Resolve the current context's endpoint before selecting a control path.
2. Prefer Pi's native `mcp__chrome_devtools__*` tools; discover them with `searchTools`.
3. If MCP is disconnected, reconnect/list its tools after the startup check.
4. If MCP still fails, direct CDP against the resolved endpoint is allowed.
5. If endpoint resolution fails, report that failure. Do not control a different browser.

## Minimum proof of browser control

A running process or visible window is not enough. Prove control with one real browser operation:

- list/select pages or targets
- read page title, URL, DOM text, console messages, or network requests
- navigate, click, type, evaluate script, or take screenshot

## Reporting rule

When reporting browser work, state which path was used:

- native `chrome-devtools` MCP tools
- direct CDP fallback
- no browser control available

Keep scope small. Do not build a new automation stack when DevTools MCP/CDP can inspect or control the existing `chromium-agent` browser.
