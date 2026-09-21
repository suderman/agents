---
name: claude-browser
description: Ask Claude questions through the user's logged-in claude.ai Project using chrome-devtools MCP. Use when the user wants a second opinion, comparison answer, or asks to "ask Claude".
---

# Claude Browser Skill

Use this skill when the user asks you to consult Claude through the browser, ask Claude a question, get a second opinion from Claude, compare your answer with Claude, or retrieve an answer from the user's logged-in Claude web session.

## Browser control

Use chrome-devtools MCP tools as the primary control path. Work from the latest snapshot and use UID values from that snapshot.

- Use `chrome-devtools_list_pages`, `chrome-devtools_select_page`, `chrome-devtools_new_page`, `chrome-devtools_navigate_page` for tab/page setup.
- Use `chrome-devtools_take_snapshot` for DOM/accessibility inspection.
- Use `chrome-devtools_click uid="..."` with snapshot UIDs for clicks.
- Use `chrome-devtools_fill uid="..."` with snapshot UIDs for text inputs.
- Use `chrome-devtools_evaluate_script` only when snapshot/click/fill cannot perform a stable action or for reading structured page state.
- Use `chrome-devtools_wait_for` or repeated snapshots for waiting.
- Use `chrome-devtools_press_key` only as a fallback when no send button is available.

Claude must remain inside the `opencode` project. Automated Claude chats should live inside this project.

## Entry URL

For the most reliable project-scoped flow, start from the Claude projects index:

```
https://claude.ai/projects
```

Then click the project named `opencode` using the UID from a snapshot.

Direct project URL, useful as a fallback or verification target:

```
https://claude.ai/project/019dd048-be96-755c-8349-f76d8c66ed29
```

## Core Rules

- Use the user's existing logged-in Claude browser session.
- If Claude is not logged in, stop. Ask the user to log in manually and create an active logged-in session, then retry.
- Dismiss overlays, popups, marketing banners, "What's new" dialogs, cookie banners, upgrade prompts, or similar interruptions before proceeding.
- Ensure Extended thinking / extended reasoning is enabled before submitting a prompt, if the Claude UI exposes such a setting for the current model/session.
- Submit the prompt by clicking the Send button using `chrome-devtools_click` with the UID from a snapshot. Prefer the button with accessible name "Send message".
- Allow Claude enough time to generate the answer. This may take 30 seconds to 5 minutes depending on complexity and network speed.
- Summarize the final answer and any relevant details when returning the result to the user.
- Keep track of the browser tab for follow-up questions. Continue in the same tab when the user's next request is a follow-up. For unrelated questions, return to `https://claude.ai/projects`, click `opencode`, and use that project page composer. Do not use the global `New chat` button.
- Do not send secrets, credentials, private keys, tokens, client-private data, or sensitive personal/financial material to Claude unless the user explicitly approves that exact prompt.
- Do not pretend Claude's answer is your own work. Clearly separate what Claude said from your own assessment.

## Tab Continuity

Prefer the current Claude project tab if it is already open and still relevant.

Use `chrome-devtools_list_pages` to find existing tabs.

If the current task is a follow-up, reuse the existing active Claude tab from the previous request.

If the previous tab is lost, closed, unresponsive, or clearly unrelated, open a new tab and navigate to the projects index, then click the `opencode` project.

For unrelated new questions, return to the projects index, click `opencode`, and use the project page composer rather than polluting an existing thread.

## Project-scoped chat verification

Claude project chats may end up at URLs like `https://claude.ai/chat/<uuid>`, even when they belong to a project. Do not decide project membership from the URL alone.

Use visible page evidence instead. A valid project-scoped chat/page should show project context such as `opencode`, "Project content", "Memory", "Instructions", "Files".

On the project landing page, the valid project composer is the large rounded input box under the `opencode` title. It may already contain stale draft text such as `hello`. This is still the correct composer. The stale text is not a previous message and is not a reason to leave the page.

Most reliable project flow for unrelated questions:

1. Navigate to `https://claude.ai/projects`.
2. Click the project named `opencode` using the UID from a snapshot.
3. Verify project context is visible (`opencode`, and ideally `Project content / opencode`).
4. Inspect the composer. If it contains stale draft text from a previous session, clear it.
5. Type the user's prompt into the composer on that project page.
6. Submit.

Do **not** click the sidebar `New chat` button after entering the project. On Claude, that control can route to `/new` and create a non-project chat.

If the project composer already contains text, that is not a reason to click `New chat`. Clear the composer and reuse it. Leaving project scope is worse than dealing with stale input.

Do **not** navigate to an existing chat for an unrelated question just because the project landing composer has stale text. That pollutes an old thread. Clear the project composer instead.

Red flags that you left project scope:

```
https://claude.ai/new
Good afternoon, Jon
How can I help you today?
Write
Learn
Code
Life stuff
```

If you see `/new` or the generic home composer after clicking `New chat`, stop. Navigate back to `https://claude.ai/projects`, click `opencode`, verify project context, and use the project composer.

## Basic Workflow

### 1. Check browser availability

Use `chrome-devtools_list_pages` to see open tabs. If no relevant tabs exist, open a new one with `chrome-devtools_new_page`.

If the chrome-devtools connection is unavailable, report the problem directly.

### 2. Open or reuse the Claude project tab

First inspect existing tabs:

```
chrome-devtools_list_pages
```

If there is a relevant Claude tab for this session and the user is asking a follow-up, use `chrome-devtools_select_page` to switch to it.

Otherwise open a new tab and navigate to the projects index:

```
chrome-devtools_new_page url="https://claude.ai/projects"
```

Then click the project named `opencode` using the UID from a snapshot. This is more reliable than starting from `/new` or using global chat controls because it gives a visible project-selection step.

### 3. Dismiss overlays

After initial page load, take a snapshot:

```
chrome-devtools_take_snapshot
```

Dismiss any overlay, modal, banner, or marketing prompt that blocks the input. Click dismiss controls using their UIDs from the snapshot. Do not click destructive or account-changing actions. Avoid anything that subscribes, upgrades, changes plans, enables sharing, or modifies account settings.

After each dismissal, take another snapshot. Continue until the prompt composer is reachable or until blocked by login/verification.

### 4. Verify logged-in state

Take a snapshot and inspect the page text:

```
chrome-devtools_take_snapshot
```

If the page shows login/signup state, such as "Log in", "Sign in", "Sign up", "Continue with Google", "Continue with Apple", or "Continue with email", stop and tell the user:

```
Claude is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

If Claude shows human verification, CAPTCHA, unusual activity, Cloudflare challenge, or account prompt that requires the human, stop and ask the user to complete it manually.

### 5. Choose the right project composer

For follow-up questions, stay in the existing Claude chat only if it is clearly the same conversation.

For unrelated new questions, do **not** open an existing chat from the project recents list. Existing chats are old threads. Use the project landing page composer instead.

For unrelated new questions:

1. Navigate to `https://claude.ai/projects`.
2. Click the project named `opencode` using the UID from a snapshot.
3. Verify the resulting page shows project context (`opencode`, and ideally `Project content / opencode`).
4. Use the large rounded composer on that project page directly, even if it contains stale draft text like `hello`.

Do not click the sidebar/global `New chat` control. It commonly routes to `https://claude.ai/new`, which loses project scope. If the composer already has a stale draft, clear it; do not navigate to `/new`.

Before typing, verify you are not on the generic home composer by checking the snapshot. If the page text contains `Good afternoon, Jon`, `How can I help you today?`, and no visible `Project content / opencode`, you are probably on `/new`. Navigate back to `https://claude.ai/projects` and click `opencode` again.

If the page text contains `opencode` plus `Memory`, `Instructions`, and `Files`, and the visible page shows a large rounded input box under the `opencode` title, that is the correct project composer. Do not search for another textbox. Clear and type into it.

Before typing, always clear any pre-existing unsubmitted text from the input field using `chrome-devtools_fill` with the textbox UID and an empty string.

If `chrome-devtools_fill` does not clear the composer, use `chrome-devtools_click` to focus the textbox first, then fill with empty string.

If it is still not clear, stop and report that the stale draft could not be cleared. Do **not** click global `New chat` as a workaround.

### 6. Ensure Extended thinking is enabled

Before submitting, take a snapshot and inspect the composer/model controls.

Find the model/thinking/reasoning controls. Ensure Extended thinking / extended reasoning is enabled if available.

Possible workflow:

1. Open the model/tools/thinking selector near the composer.
2. Choose the current model option that supports extended thinking, if model selection is exposed.
3. Choose or enable `Extended thinking`, `Extended`, `Think`, `Thinking`, or equivalent.
4. Verify the visible state indicates extended thinking is active.

Selector ideas will change as Claude's UI changes. Prefer snapshot-driven interaction over hard-coded selectors.

Look for controls or labels such as "Thinking", "Think", "Reason", "Reasoning", "Extended", "Extended thinking", "More", "Tools", "Model".

If Extended thinking is not available in the current model/project/session, do not silently proceed. Report the limitation and ask the user whether to continue without Extended thinking.

### 7. Type the prompt

Prepare a concise, self-contained prompt. Type it directly as the user — do **not** prepend any disclosure about being an agent, second-opinion assistant, coding workflow, or similar framing. The user is asking directly; present it that way.

Prompt template — use directly, verbatim:

```
<USER_TASK>
```

Focus the Claude input field and type the prompt using `chrome-devtools_fill` with the UID from a snapshot.

### 8. Submit the prompt

After the input field has focus and the prompt text is present, submit by clicking the Send button using `chrome-devtools_click` with the UID from a snapshot.

**Primary submit method:** Look for a button with accessible name "Send message".

Do not rely on `chrome-devtools_press_key` — it does not reliably trigger submission on claude.ai.

### 9. Wait for completion

Allow 30 seconds to 5 minutes.

Poll periodically by taking snapshots:

```
chrome-devtools_take_snapshot
```

The response is probably still streaming if:

- a Stop button is visible
- the latest assistant response is still changing
- a spinner/progress indicator is visible
- the composer is disabled
- the Send button has not returned
- the latest response has no Copy button yet

Consider the answer complete when:

- the Stop button disappears
- the Send button or composer returns
- page text is stable across two polls
- a Copy button appears under the latest assistant message
- no progress indicator is visible

For complex prompts, keep waiting up to about 5 minutes unless there is an obvious error.

### 10. Extract the final answer

Prefer the cleanest extraction method available.

Best option:

1. Use `chrome-devtools_take_snapshot` to locate the Copy button nearest the latest assistant response.
2. Click that Copy button using its UID.
3. Read the clipboard with shell if allowed:

```bash
wl-paste
```

Fallbacks:

```bash
xclip -selection clipboard -o
xsel -b
```

If clipboard extraction is unavailable, use `chrome-devtools_take_snapshot` and `chrome-devtools_evaluate_script` to read page content, then extract the latest assistant message after the submitted prompt.

Avoid returning the entire noisy page. Return the final answer and relevant details only.

### 11. Return the result to the user

Use this format:

```
Claude said:

<concise summary of Claude's final answer>

Relevant details:

<any specific commands, caveats, URLs, or reasoning points worth preserving>

My read:

<your brief assessment, agreement/disagreement, missing caveats, or recommended next step>
```

If the user asked only to fetch Claude's answer, keep your own assessment short.

## Troubleshooting

### Claude is logged out

Stop and say:

```
Claude is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

### Human verification / CAPTCHA

Stop and say:

```
Claude is asking for human verification. Please complete it manually in the browser, then I can continue.
```

### Overlay blocks the page

Dismiss harmless overlays. Do not click upgrade, subscribe, enable, buy, connect account, share, or privacy-sensitive account actions.

### Extended thinking is unavailable

Stop and say:

```
I cannot find or enable Extended thinking in this Claude session. Do you want me to continue without it?
```

### Prompt typed but did not submit

Take a snapshot and click the Send button directly using its UID.

Do not spam submissions. One click is sufficient.

### Stale text in Claude composer

Correct behavior:

1. Stay on the verified `opencode` project page.
2. Use `chrome-devtools_fill` with the textbox UID and an empty string to clear it.
3. Verify stale text is gone with a fresh snapshot.
4. Type the new user prompt.

Incorrect behavior:

- Do not click global `New chat` just because the composer has stale text.
- Do not navigate to `/new` as a workaround.
- Do not append the new prompt to stale text.
- Do not open an existing chat from the project recents list for an unrelated question.
- Do not treat stale text in the project composer as a previous chat message.

### Response extraction is messy

Use the Copy button nearest the latest response. This is usually cleaner than parsing all page text.

### Multiple Claude tabs exist

Prefer the tab already used for this session when the user asks a follow-up. For unrelated questions, start a new chat inside the Claude project.

### The conversation is too long or off-topic

Start a new chat inside the Claude project.
