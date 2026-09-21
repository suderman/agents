# Selector Strategy

Choose selectors from the live rendered UI, not from guesses based on source
code.

## Preferred selector order

Prefer, in order:

1. accessible role and name
2. associated labels
3. visible text
4. stable IDs
5. stable data attributes
6. structural selectors only as a last resort

## Good selector characteristics

Good selectors are:

- stable across minor layout changes
- tied to user-visible meaning
- narrow enough to identify one target
- understandable when read later

## Avoid

Avoid selectors that depend on:

- deep nested structure
- fragile CSS class chains
- generated class names
- nth-child style positioning
- visual order that may change
- hidden implementation details

## Examples

Better:

- button with visible text "Save"
- textbox labeled "Email"
- dialog titled "Delete site"
- element with stable `data-testid`
- stable `id` tied to app meaning

Worse:

- `.flex.items-center.justify-between > div:nth-child(2) button`
- `.css-1abcde`
- `div > div > span > button`

## If there are multiple matching elements

When more than one element looks plausible:

- inspect which one is visible
- inspect which one is enabled
- inspect which one is inside the active dialog/panel/section
- use surrounding context from the live page

## Rule

If a selector feels clever, it is probably too brittle.
