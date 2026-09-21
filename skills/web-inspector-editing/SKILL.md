---
name: web-inspector-editing
description: Inspect live websites and safely test temporary CSS and JS edits through browser control tools. Always reload between edit attempts so each experiment starts from a clean page state.
license: CC0-1.0
---

# Web Inspector Editing

Use this skill when you need to inspect a live website URL and try temporary CSS
or JavaScript edits in the browser before recommending a final change.

Load `browser-control-basics` first for the shared environment rules around MCP,
direct CDP fallback, and what counts as real browser control.

When testing live CSS or JavaScript changes, use the existing agent-controlled
Chromium instance from `chromium-agent`. If chrome-devtools MCP is unavailable,
use direct CDP fallback rather than launching a separate browser.

This skill is for:

- testing CSS overrides on a live page
- trying temporary JavaScript fixes without editing source files
- inspecting rendered DOM and computed layout before changing anything
- validating visual changes with screenshots
- comparing multiple browser-side experiments safely

Prefer browser tools over guesswork.

## Core rule

Every new edit attempt must begin from a fresh page state.

That means:

1. reload the page before each distinct CSS or JS experiment
2. wait for the relevant content to appear again
3. then inject the new test code

Do not stack experiments on top of each other and assume the result is valid.

## When to use this skill

Use it when the user asks for things like:

- "try a CSS override on this live page"
- "inspect this website and see how a JS tweak would behave"
- "test a layout fix in Chrome before giving me the code"
- "use the browser tools to see what selector actually works"

## Clean-attempt workflow

Follow this loop for each attempt.

1. Open or select the target page.
2. Reload with cache bypass when possible.
3. Wait for the target text or UI to appear.
4. Inspect the rendered DOM and computed layout.
5. Inject one temporary CSS or JS experiment.
6. Measure the result with script evaluation or runtime inspection.
7. Capture a screenshot.
8. Decide whether the attempt succeeded.
9. Before trying a different approach, reload and start over.

## Do not trust old browser state

Browser state can be contaminated by previous injected `<style>` or `<script>`
tags, cached assets, or mutated DOM.

If a plain reload does not return the page to a clean state:

- use a cache-busting query string such as `?v=2` or `?v=3`
- open a fresh tab in a separate isolated context if needed
- verify the page no longer contains your prior injected test code before
  proceeding

## Recommended reconnaissance

Before injecting edits, inspect:

- the current viewport size
- the target element hierarchy
- computed widths, heights, margins, and display values
- whether the page is using flex, grid, floats, or fixed widths
- whether the target content is actually present on the live page
- whether recent content might be missing because of caching

Use evidence from the rendered page, not assumptions from source alone.

## CSS testing guidance

For CSS experiments:

- inject a `<style>` tag with a unique id using script evaluation
- scope selectors as narrowly as practical
- prefer additive overrides instead of destructive rewrites
- use `!important` only when needed to beat existing specificity
- verify layout numerically after injection, not just visually

Useful checks include:

- `getBoundingClientRect()` for width, left, top, and height
- `getComputedStyle()` for display, flex, grid, margin, max-width, and
  background sizing
- checking whether multiple cards share the same `top` value to confirm they are
  on one row

## JavaScript testing guidance

For JS experiments:

- keep the script small and reversible
- avoid permanent app mutations unless the user explicitly wants them tested
- prefer one focused behavior change per attempt
- expose enough measurable output to verify success
- inspect console messages after running the script if behavior is unexpected

## Attempt hygiene

Good:

- reload before each new approach
- inject one experiment
- measure
- screenshot
- summarize

Bad:

- stacking multiple style tags and forgetting which one is active
- trying a second CSS idea without a reload
- assuming a missing element is a selector problem when it may be caching
- giving the user final CSS without validating it in the browser

## Practical browser pattern

For each attempt, prefer a sequence like:

1. Reload with cache ignored when possible
2. Wait for relevant text or UI to appear
3. Inspect the DOM and computed values
4. Inject one temporary CSS or JS experiment
5. Measure the result with script evaluation
6. Capture a screenshot to confirm visually when layout matters

## What success looks like

A browser edit attempt is successful only when all of the following are true:

- the page was freshly reloaded before the attempt
- the target content was confirmed present in the live DOM
- the injected change produced the intended effect
- the result was checked with measurements or computed styles
- the result was confirmed visually with a screenshot when layout matters

## Final handoff guidance

When reporting back to the user:

- clearly distinguish temporary injected test code from final recommended code
- if caching affected the test, mention it explicitly
- if a previous attempt was invalid because the page was dirty, say so
- briefly state whether you used MCP or direct CDP fallback
- provide the smallest final CSS or JS override that matched the successful
  browser-tested attempt
