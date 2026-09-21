---
name: browser-testing
description: Test and debug web applications using an already-running Chromium instance. Prefers reconnaissance-first browser inspection, screenshots, console/network inspection, and rendered-DOM analysis before taking action.
license: CC0-1.0
---

# Browser Testing

Use this skill when working on web applications that can be inspected through
an existing Chromium instance.

Load `browser-control-basics` first for the shared environment rules around MCP,
direct CDP fallback, and what counts as real browser control.

This skill is for:

- verifying frontend functionality
- reproducing UI bugs
- inspecting rendered DOM state
- collecting console errors and network failures
- taking screenshots during testing
- validating fixes in the running app

Prefer existing browser-control paths over writing fresh automation scripts.
Only write scripts when repeated execution or complex multi-step validation is
genuinely needed.

## Core rule

Do not guess.

For dynamic web apps, first inspect the live rendered application, then choose
selectors and actions from what actually exists in the browser.

## Preferred workflow

Prefer the existing running Chromium session over launching a separate browser
stack.

Use the available browser-control path first. Only fall back to a separate
automation stack if:

- browser tools are unavailable
- the existing Chromium instance cannot be reached
- the task truly requires a dedicated scripted runner

## Decision tree

User task → Is it static HTML or mostly server-rendered with predictable markup?

- Yes:
  1. Read the HTML/templates directly if useful
  2. Identify likely selectors
  3. Confirm them in the browser if possible
  4. Perform actions and verify results

- No, it is dynamic:
  1. Ensure the app is running
  2. Connect to the existing Chromium session using the available browser-control path
  3. Navigate to the relevant page
  4. Wait for the page to settle
  5. Inspect rendered DOM, console, network activity, and screenshots
  6. Identify selectors from the live state
  7. Perform actions
  8. Re-check browser state after each meaningful step

## Reconnaissance-then-action pattern

For dynamic pages, always do reconnaissance before interaction.

1. Open the page
2. Wait for the app to settle after navigation and major UI changes
3. Capture evidence:
   - screenshot
   - visible text
   - DOM structure
   - console messages
   - failed network requests
4. Identify the real selectors from the rendered state
5. Act using those selectors
6. Verify the result in the browser, not just in code

## What to inspect

Before taking action, prefer inspecting:

- headings and visible labels
- buttons, links, inputs, dialogs
- element roles / accessible names
- console warnings and errors
- failed API requests
- loading states, disabled states, hidden elements
- post-render DOM rather than source HTML alone

## Waiting guidance

Do not inspect too early.

For dynamic apps, wait for:

- initial page load to complete
- obvious loading indicators to disappear
- the relevant component or text to appear
- network activity to calm down, when that matters

After clicks, form submissions, route changes, or filter changes, wait again
before concluding success or failure.

## Common pitfalls

Bad:

- guessing selectors from source code alone
- acting before the app has rendered
- assuming a click succeeded without checking the page state
- ignoring console and network failures
- opening unrelated source files too early and polluting context

Good:

- inspect first
- act second
- verify third

## Browser-first debugging procedure

When something looks broken:

1. Reproduce it in the live app
2. Capture screenshot(s)
3. Check console output
4. Check network failures
5. Inspect the affected DOM region
6. Form a concrete hypothesis
7. Change the code
8. Retest in the browser
9. Confirm the fix visually and functionally

## Selector guidance

Prefer selectors based on the user-visible UI:

- role
- label
- text
- stable IDs or data attributes

Avoid brittle selectors tied to incidental structure unless there is no better
option.

## Scope discipline

Use browser tools as black boxes where possible.

Do not read large helper scripts, tool internals, or unrelated app files unless:

- the browser evidence is insufficient
- you need implementation details to explain the observed behavior
- a custom scripted step is truly necessary

## Success criteria

A task is not done just because code changed.

It is done when the running app has been checked and the expected behavior is
visible in the browser.

## Additional resources

Read these only as needed.

- For reconnaissance before interacting with the app, see
  [reconnaissance.md](reconnaissance.md)
- For choosing robust selectors from the live UI, see
  [selector-strategy.md](selector-strategy.md)
- For browser runtime evidence like console errors and failed requests, see
  [console-and-network.md](console-and-network.md)
- For post-fix validation, see [verification.md](verification.md)
- For worked debugging/testing patterns, see [examples.md](examples.md)

Do not load all of these up front. Read only the file(s) relevant to the current
task.
