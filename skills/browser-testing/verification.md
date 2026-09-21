# Verification

A code change is not the same thing as a fix.

## Verification checklist

After making a change:

1. reload or revisit the relevant page if needed
2. reproduce the original scenario
3. perform the same user actions again
4. inspect the resulting UI
5. confirm no new console or network failures were introduced
6. confirm the result matches the expected behavior

## What counts as verified

A change is verified when:

- the original bug no longer appears
- the expected UI state is visible
- the interaction works end-to-end
- the browser shows no relevant new errors
- the behavior is repeatable

## Avoid false positives

Do not stop at:

- "the code looks right now"
- "the branch compiles"
- "the click seemed to work once"
- "the DOM element exists somewhere"

## Regressions

When practical, check nearby behavior too:

- sibling actions in the same component
- open/close flows for dialogs
- form validation around the changed area
- empty states, loading states, and error states

## Rule

Verification must happen in the running app, not only in your head or editor.
