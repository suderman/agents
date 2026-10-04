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

Load `browser-control-basics` first. Agents share the browser on CDP port 9222;
Herdr workspace identity does not affect browser selection. Agent windows open
on Hyprland workspace 8.

## Startup check

Check the shared browser:

```sh
endpoint=http://127.0.0.1:9222
curl -fsS --max-time 2 "$endpoint/json/version"
```

If absent, start `chromium-agent` in the background and repeat the check. The
wrapper restarts the shared agent browser, so reuse a working endpoint instead
of launching again. `chromium-agent --help` does not launch a browser.

Pi's MCP configuration uses `--browser-url=http://127.0.0.1:9222`. If tools are
unavailable, reconnect through `/mcp` or use direct CDP against the same endpoint.
Do not select a personal browser or an old trial profile.

## Control path order

1. Check the shared agent endpoint before selecting a control path.
2. Prefer Pi's native `mcp__chrome_devtools__*` tools; discover them with `searchTools`.
3. If MCP is disconnected, reconnect/list its tools after the startup check.
4. If MCP still fails, direct CDP against the shared endpoint is allowed.
5. If the agent browser cannot start or expose CDP, report that failure. Do not control a different browser.

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
