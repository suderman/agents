# Reconnaissance

For dynamic web apps, reconnaissance comes before action.

## Goal

Understand what the app is actually doing right now in the browser before
interacting with it or changing code.

## Procedure

1. Open the relevant page or route
2. Wait for the page to settle
3. Capture the visible state
4. Inspect the relevant area of the DOM
5. Check console output
6. Check network failures or suspicious responses
7. Only then choose selectors and actions

## What to capture

Always try to gather some combination of:

- screenshot
- current URL
- visible headings and labels
- relevant buttons, inputs, dialogs, tabs, menus
- rendered DOM for the problem area
- console messages
- failed or slow network requests
- loading, disabled, hidden, or error states

## Waiting discipline

Do not inspect too early.

Wait for:

- initial rendering to complete
- loading indicators to disappear
- the relevant component or text to appear
- route changes to finish
- async data to populate the UI

After any major action like:

- clicking a button
- submitting a form
- switching tabs
- filtering content
- opening a modal

wait again before concluding anything.

## Good questions during reconnaissance

- What exactly is visible?
- What is missing that should be visible?
- Is the UI disabled, hidden, or stale?
- Is the DOM different from what the source code suggested?
- Are there console errors?
- Are requests failing, hanging, or returning unexpected data?
- Is the problem reproducible every time?

## Output of reconnaissance

By the end of reconnaissance, you should be able to say:

- what the user sees
- what the browser is doing
- which element(s) matter
- what you think is wrong
- what you want to test next
