---
name: chatgpt-browser
description: Ask ChatGPT questions through the user's logged-in chatgpt.com Project using chrome-devtools MCP. Use when the user wants a second opinion, comparison answer, or asks to "ask ChatGPT".
---

# ChatGPT Browser Skill

Use this skill when the user asks you to consult ChatGPT through the browser, ask ChatGPT a question, get a second opinion from ChatGPT, compare your answer with ChatGPT, or retrieve an answer from the user's logged-in ChatGPT web session.

## Browser control

Use chrome-devtools MCP tools as the primary control path. Work from the latest snapshot and use UID values from that snapshot.

- Use `chrome-devtools_list_pages`, `chrome-devtools_select_page`, `chrome-devtools_new_page`, `chrome-devtools_navigate_page` for tab/page setup.
- Use `chrome-devtools_take_snapshot` for DOM/accessibility inspection.
- Use `chrome-devtools_click uid="..."` with snapshot UIDs for clicks.
- Use `chrome-devtools_fill uid="..."` with snapshot UIDs for text inputs.
- Use `chrome-devtools_evaluate_script` only when snapshot/click/fill cannot perform a stable action or for reading structured page state.
- Use `chrome-devtools_wait_for` or repeated snapshots for waiting.
- Use `chrome-devtools_press_key` only as a fallback when no send button is available.

## Entry URL

For the most reliable project-scoped flow, start from the ChatGPT home page:

```
https://chatgpt.com/
```

Then find the project named `opencode` in the sidebar and click it.

Direct project URL, useful as a fallback or verification target:

```
https://chatgpt.com/g/g-p-69efac46be008191ac624f637e3d8bdf/project?tab=chats
```

This is the user's ChatGPT Project named `opencode`. Automated ChatGPT chats should live inside this project.

## Core Rules

- Use the user's existing logged-in ChatGPT browser session.
- If ChatGPT is not logged in, stop. Ask the user to log in manually and create an active logged-in session, then retry.
- Dismiss overlays, popups, marketing banners, "What's new" dialogs, cookie banners, upgrade prompts, or similar interruptions before proceeding.
- Ensure Thinking effort is enabled and set to `Extended` before submitting a prompt.
- Submit the prompt by clicking ChatGPT's send button using `chrome-devtools_click` with the UID from a snapshot. Prefer the button with accessible name matching "Send prompt".
- Allow ChatGPT enough time to generate the answer. This may take 30 seconds to 5 minutes depending on complexity and network speed.
- Summarize the final answer and any relevant details when returning the result to the user.
- Keep track of the browser tab for follow-up questions. Continue in the same tab when the user's next request is a follow-up. For unrelated questions, return to `https://chatgpt.com/`, click the `opencode` project in the sidebar, and use the project-scoped composer/chat controls.
- Do not send secrets, credentials, private keys, tokens, client-private data, or sensitive personal/financial material to ChatGPT unless the user explicitly approves that exact prompt.
- Do not pretend ChatGPT's answer is your own work. Clearly separate what ChatGPT said from your own assessment.

## Tab Continuity

Prefer the current ChatGPT project tab if it is already open and still relevant.

Use `chrome-devtools_list_pages` to find existing tabs.

If the current task is a follow-up, reuse the existing active ChatGPT tab from the previous request.

If the task is unrelated, do not click an existing chat title from the project chat list. Existing chats are old threads. Start from ChatGPT home and click the `opencode` project in the sidebar.

If the previous tab is lost, closed, unresponsive, or clearly unrelated, open a new tab and navigate to ChatGPT home, then click the `opencode` project in the sidebar.

For unrelated new questions, create a fresh chat inside the `opencode` project rather than polluting an existing thread. Do not decide project membership from the URL alone; verify visible project context.

## Project-scoped chat verification

ChatGPT project chats may use URLs that do not obviously show the project. Do not decide project membership from the URL alone.

Use visible page evidence instead. A valid project-scoped page/chat should show the `opencode` project context somewhere in the sidebar, header, project panel, or chat list.

Most reliable project flow for unrelated questions:

1. Navigate to `https://chatgpt.com/`.
2. Find and click the project named `opencode` in the sidebar.
3. Verify visible project context shows `opencode`.
4. Use the project-scoped composer/chat controls from there.
5. If the composer contains stale draft text from a previous session, clear it instead of leaving project scope.
6. Type the prompt.
7. Submit by clicking the send button using the UID from a snapshot.

If the project composer already contains text, that is not a reason to leave the project, click a global new-chat control, or open an unrelated existing chat. Clear the composer and reuse the project-scoped flow.

Fast path when a project tab is already open but uncertain: navigate that tab to `https://chatgpt.com/`, click `opencode` in the sidebar, verify project context, then type and submit. Do not spend time opening old chats to inspect them.

## Basic Workflow

### 1. Check browser availability

Use `chrome-devtools_list_pages` to see open tabs. If no relevant tabs exist, open a new one with `chrome-devtools_new_page`.

If the chrome-devtools connection is unavailable, report the problem directly.

### 2. Open or reuse the ChatGPT project tab

First inspect existing tabs using `chrome-devtools_list_pages`.

If there is a relevant ChatGPT tab for this session and the user is asking a follow-up, use `chrome-devtools_select_page` to switch to it.

Otherwise open a new tab and navigate to ChatGPT home:

```
chrome-devtools_new_page url="https://chatgpt.com/"
```

Then find the project named `opencode` in the sidebar and click it using `chrome-devtools_click` with the UID from a snapshot. Use the direct project URL only as a fallback if the sidebar route is unavailable.

### 3. Dismiss overlays

After initial page load, take a snapshot:

```
chrome-devtools_take_snapshot
```

Dismiss any overlay, modal, banner, or marketing prompt that blocks the input.

Click dismiss controls using their UIDs from the snapshot. Do not click destructive or account-changing actions. Avoid anything that subscribes, upgrades, changes plans, enables sharing, or modifies account settings.

After each dismissal, take another snapshot. Continue until the prompt composer is reachable or until blocked by login/verification.

### 4. Verify logged-in state

Take a snapshot and inspect the page text:

```
chrome-devtools_take_snapshot
```

If the page shows login/signup state, such as "Log in", "Sign up", "Continue with Google", "Continue with Apple", or "Continue with Microsoft", stop and tell the user:

```
ChatGPT is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

If ChatGPT shows human verification, CAPTCHA, unusual activity, Cloudflare challenge, or account prompt that requires the human, stop and ask the user to complete it manually.

### 5. Create or choose the right project chat

For follow-up questions, stay in the existing ChatGPT chat only if it is clearly the same conversation.

For unrelated new questions:

1. Navigate to `https://chatgpt.com/`.
2. Find and click the project named `opencode` in the sidebar using UIDs from a snapshot.
3. Verify visible project context shows `opencode`.
4. Create or use a fresh project-scoped chat from there.
5. If using any new-chat control, verify `opencode` remains visible afterward before typing.

Do not open an unrelated existing chat from the project recents list just because the project page has a stale draft. Existing chats are old threads.

Before typing, clear any pre-existing unsubmitted text from the input field using `chrome-devtools_fill` with the UID of the textbox and empty string.

Then verify stale draft text is gone by taking another snapshot.

If stale text cannot be cleared, stop and report that the stale draft could not be cleared. Do not leave project scope as a workaround.

### 6. Ensure Thinking effort is Extended

Before submitting, inspect the composer/model controls using a snapshot.

Find the Thinking / reasoning effort control. Ensure it shows "Extended" or equivalent UI state.

Possible workflow:

1. Open the model/tools/thinking selector near the composer.
2. Choose `Thinking` if it is disabled.
3. Choose `Extended` as the effort level.
4. Verify the visible state indicates Extended thinking.

Selector ideas will change as ChatGPT's UI changes. Prefer snapshot-driven interaction over hard-coded selectors.

Look for controls or labels such as "Thinking", "Think", "Reason", "Reasoning", "Effort", "Extended", "More", "Tools".

If Extended thinking is not available in the current model/project/session, do not silently proceed. Report the limitation and ask the user whether to continue without Extended thinking.

### 7. Type the prompt

Prepare a concise, self-contained prompt. Type it directly as the user — do **not** prepend any disclosure about being an agent, second-opinion assistant, coding workflow, or similar framing. The user is asking directly; present it that way.

Prompt template — use directly, verbatim:

```
<USER_TASK>
```

Focus the ChatGPT input field using `chrome-devtools_fill` with the UID from a snapshot. Use the textbox UID found in the snapshot.

### 8. Submit the prompt

After the input field has the prompt text, submit by clicking ChatGPT's send button using `chrome-devtools_click` with the UID from a snapshot.

Look for a button with accessible name matching "Send prompt" or "Send".

Do **not** use `chrome-devtools_press_key` as the primary submit path. It can time out and is slower than clicking the real send button.

Do not spam submissions. One successful click is sufficient.

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
ChatGPT said:

<concise summary of ChatGPT's final answer>

Relevant details:

<any specific commands, caveats, URLs, or reasoning points worth preserving>

My read:

<your brief assessment, agreement/disagreement, missing caveats, or recommended next step>
```

If the user asked only to fetch ChatGPT's answer, keep your own assessment short.

## Troubleshooting

### ChatGPT is logged out

Stop and say:

```
ChatGPT is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

### Human verification / CAPTCHA

Stop and say:

```
ChatGPT is asking for human verification. Please complete it manually in the browser, then I can continue.
```

### Overlay blocks the page

Dismiss harmless overlays. Do not click upgrade, subscribe, enable, buy, connect account, share, or privacy-sensitive account actions.

### Extended thinking is unavailable

Stop and say:

```
I cannot find or enable Extended thinking in this ChatGPT session. Do you want me to continue without it?
```

### Prompt typed but did not submit

Take a snapshot and click the send button directly using its UID from the snapshot.

### Stale text in ChatGPT project composer

Correct behavior:

1. Stay in the verified `opencode` project context.
2. Use `chrome-devtools_fill` with the textbox UID and an empty string to clear it.
3. Verify stale text is gone with a fresh snapshot.
4. Type the new user prompt.

Incorrect behavior:

- Do not leave the `opencode` project just because the composer has stale text.
- Do not append the new prompt to stale text.
- Do not open an unrelated existing chat from the project recents list for an unrelated question.
- Do not decide project scope from URL alone; verify visible `opencode` context.

### Response extraction is messy

Use the Copy button nearest the latest response. This is usually cleaner than parsing all page text.

### Multiple ChatGPT tabs exist

Prefer the tab already used for this session when the user asks a follow-up. For unrelated questions, return to `https://chatgpt.com/`, click the `opencode` project in the sidebar, and verify project context before typing.

### The conversation is too long or off-topic

Return to `https://chatgpt.com/`, click the `opencode` project in the sidebar, and start from verified project context.
