---
name: browser-control-basics
description: Use Chromium safely and predictably in this environment. Covers MCP versus direct CDP, what counts as real browser control, and the minimum verification/reporting rules.
license: CC0-1.0
---

# Browser Control Basics

Use this skill when a task involves driving, inspecting, or validating behavior
in Chromium.

This skill defines the shared environment rules for browser control. Load it
before using more specialized browser skills.

## Expected browser

This setup expects browser automation to use the Chromium instance launched by:

```sh
chromium-agent
```

Do not launch raw `chromium`, `google-chrome`, or a fresh browser profile for
agent-controlled browser work unless explicitly instructed.

Prefer the existing browser owned by the caller's context over launching a
separate browser stack. A running browser in another Herdr workspace is not
this context's browser.

## Environment note

In this environment, `chrome-devtools` MCP may be unavailable or disconnected
even when Chromium is running and reachable over CDP.

Treat MCP availability and browser controllability as separate concerns.

## Startup check

Resolve the caller's endpoint before using MCP or direct CDP:

```sh
if [ -n "${HERDR_WORKSPACE_ID:-}" ] && command -v herdr-hypr >/dev/null; then
  endpoint=$(herdr-hypr cdp --start) || exit 1
else
  endpoint=http://127.0.0.1:9222
fi
curl -fsS --max-time 2 "$endpoint/json/version"
```

Inside the Herdr/Hyprland trial, `cdp --start` reuses or starts only the current
workspace's isolated browser and waits for its endpoint. `herdr-hypr cdp` checks
without starting it. A failed lookup is a failure, not permission to use another
browser. Never read another workspace's `DevToolsActivePort`, scan ports for a
reachable browser, or fall back to 9222 in this mode. Do not fake Herdr identity.

Outside the trial, keep the existing global agent browser on 9222. If absent,
launch `chromium-agent` in the background, then repeat the endpoint check.
`chromium-agent --help` does not start a browser.

Pi's trial MCP launcher is `herdr-hypr devtools`; it resolves and starts the same
owned browser. If MCP tools are missing, reconnect through `/mcp` after resolving
the endpoint. A session whose pane moved to another Herdr workspace must reconnect
before using existing browser tools. Direct CDP fallback must use the resolved
`$endpoint`, never a port discovered from another profile.

## Allowed control paths

If the user asks for browser automation or inspection:

- use MCP when it is available and appropriate
- if MCP is unavailable, direct CDP fallback is allowed when possible
- if both MCP and CDP fail, check `chromium-agent` before debugging the MCP
  server

## What does not prove control

Do not assume browser control just because:

- a Chromium process exists
- a URL opens in the browser
- a page is visible on screen

Real browser control should be verified with an actual inspection or browser
action, such as:

- listing or selecting targets
- reading DOM state, console output, or network failures
- evaluating script in the page
- clicking, typing, navigating, or taking a screenshot

## Reporting rule

Briefly state which control path you used:

- MCP
- direct CDP fallback
- no browser control available

## Scope discipline

Use the smallest capable control path for the task.

Do not build a fresh automation stack unless:

- browser control paths are unavailable
- the task genuinely needs a dedicated scripted runner
- repeated execution makes scripting clearly worthwhile
