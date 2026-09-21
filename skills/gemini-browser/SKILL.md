---
name: gemini-browser
description: Ask Gemini questions through the user's logged-in gemini.google.com browser session using chrome-devtools MCP. Use when the user wants a second opinion, comparison answer, or asks to "ask Gemini".
---

# Gemini Browser Skill

Use this skill when the user asks you to consult Gemini through the browser, ask Gemini a question, get a second opinion from Gemini, compare your answer with Gemini, or retrieve an answer from the user's logged-in Gemini web session.

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

Always enter Gemini through:

```
https://gemini.google.com/app
```

Note: use the URL **without** a trailing slash. The URL with a trailing slash may return 404.

Use the user's existing logged-in Gemini browser session.

## Core rules

- Use the user's existing logged-in Gemini browser session.
- If Gemini is not logged in, stop. Ask the user to log in manually and create an active logged-in session, then retry.
- Dismiss overlays, popups, marketing banners, "What's new" dialogs, cookie banners, upgrade prompts, subscription prompts, and similar interruptions before proceeding.
- **Mode requirement**: Before submitting, change Gemini's mode from `Fast` to `Pro`. Treat `Pro` as the required preferred mode.
  - If `Pro` is unavailable because quota usage for Pro is exhausted or unavailable, fall back to `Thinking`.
  - If neither `Pro` nor `Thinking` can be enabled or verified, stop and ask whether to continue in the current mode. Do not silently proceed.
- Submit by clicking Gemini's send/submit button using `chrome-devtools_click` with the UID from a snapshot.
- Ask directly as the user. Do **not** prepend disclosure text like "I am using you as a second-opinion assistant".
- Allow Gemini enough time to generate the answer. This may take 30 seconds to 5 minutes depending on complexity and network speed.
- Do not send secrets, credentials, private keys, tokens, client-private data, or sensitive personal/financial material unless the user explicitly approves that exact prompt.
- Do not pretend Gemini's answer is your own work. Clearly separate what Gemini said from your own assessment.

## Basic workflow

### 1. Check browser availability

Use `chrome-devtools_list_pages` to see open tabs. If no relevant tabs exist, open a new one with `chrome-devtools_new_page`.

If the chrome-devtools connection is unavailable, report the problem directly.

### 2. Open or reuse Gemini

Prefer an existing relevant Gemini tab for follow-up questions.

For unrelated questions, open or navigate to:

```
chrome-devtools_new_page url="https://gemini.google.com/app"
```

### 3. Dismiss overlays

After page load, take a snapshot:

```
chrome-devtools_take_snapshot
```

Dismiss harmless overlays that block the page or composer using UIDs from the snapshot. Do not click destructive or account-changing actions. Avoid anything that subscribes, upgrades, purchases, changes account settings, enables sharing, connects accounts, or changes privacy settings.

After each dismissal, take another snapshot. Continue until the prompt composer is reachable or until blocked by login/verification.

### 4. Verify logged-in state

Take a snapshot and inspect the page text.

If the page shows login/signup state, such as "Sign in", "Log in", "Continue with Google", or a Google account picker without a Gemini interface, stop and tell the user:

```
Gemini is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

If Gemini shows human verification, CAPTCHA, unusual activity, or an account prompt requiring the human, stop and ask the user to complete it manually.

### 5. Choose the right mode (Fast / Pro / Thinking)

Before submitting, Gemini's mode must be set to `Pro`. This is a required step.

Take a snapshot and inspect the composer/model controls.

**Mode hierarchy:**
1. `Pro` — preferred mode
2. `Thinking` — fallback if Pro quota is exhausted/unavailable
3. `Fast` — the default; must be changed before proceeding

**Likely workflow:**

1. Inspect the snapshot for a model/mode picker toggle or dropdown near the composer. Look for labels or accessible names such as `Fast`, `Pro`, `Thinking`, `Model`, `Mode`, or a dropdown arrow/chevron.
2. Click the mode picker using its UID from the snapshot to open the mode menu.
3. Wait briefly, then take a new snapshot.
4. Find `Pro` in the menu and click it using its UID.
5. Take a fresh snapshot and verify the visible mode shows `Pro` or equivalent preferred state.

**Hard gate**: Do not proceed to type the prompt until `Pro` is visibly verified. If `Pro` is not confirmed in the snapshot, do not assume it worked; re-open the mode picker and retry, or try the `Thinking` fallback.

If `Pro` is unavailable (quota exhausted, usage limits, or similar), fall back to `Thinking`:

1. Re-open the mode picker.
2. Select `Thinking` instead.
3. Verify the mode shows `Thinking`.

If neither `Pro` nor `Thinking` can be enabled or verified after two attempts each, stop and ask:

```
I cannot enable Pro mode (quota may be exhausted) and Thinking mode is also unavailable. Would you like me to continue in the current Fast mode, or stop here?
```

Do not silently proceed in `Fast` mode.

### 6. Type the prompt

Prepare a concise, self-contained prompt. Type it directly as the user.

Prompt template:

```
<USER_TASK>
```

Use `chrome-devtools_fill` with the composer textbox UID from a snapshot. Look for a textbox labeled `Enter a prompt here`, `Ask Gemini`, or similar placeholder text in the Gemini prompt composer.

Before typing, clear any stale draft text using `chrome-devtools_fill` with the textbox UID and an empty string, then verify with a fresh snapshot.

### 7. Submit the prompt

Primary submit method: Look for a button with accessible name such as "Submit", "Send", "Run", or a right-arrow/send icon in the snapshot, then click using its UID.

Do not use `chrome-devtools_press_key` as the primary submit path. It can time out and is less reliable than clicking the real send button.

Do not spam submissions. One successful click is sufficient.

**Post-submit confirmation**: After clicking submit, take a snapshot before waiting. Gemini may show an `Answer now` button or similar confirmation prompt (especially for Pro or quota-related confirmation). If visible, click it using the UID from the latest snapshot, then proceed to wait for generation.

### 8. Wait for completion

Allow 30 seconds to 5 minutes.

Poll periodically by taking snapshots:

```
chrome-devtools_take_snapshot
```

The response is probably still streaming if:

- a Stop button is visible
- response text is still changing
- a spinner/progress indicator is visible
- composer is disabled
- send button has not returned
- the latest response has no Copy button yet

Consider the answer complete when:

- stop/progress indicators disappear
- composer/send control returns
- page text is stable across two polls
- a Copy button appears near the latest assistant message

### 9. Extract the final answer

Prefer the cleanest extraction available.

Best option:

1. Use `chrome-devtools_take_snapshot` to locate the Copy button nearest the latest Gemini response.
2. Click that Copy button using its UID.
3. Read clipboard with shell if available:

```bash
wl-paste
```

**Validate clipboard content**: check that the pasted text is an actual Gemini answer and not just `https://gemini.google.com/app`, a URL, or other noisy/stale content. If clipboard content is a URL or clearly incomplete, fall back to snapshot/evaluate extraction instead.

Fallbacks:

```bash
xclip -selection clipboard -o
xsel -b
```

If clipboard extraction is unavailable, use `chrome-devtools_take_snapshot` and `chrome-devtools_evaluate_script` to read page content, then extract the latest Gemini answer after the submitted prompt. Avoid returning noisy full-page text.

### 10. Return the result

Use:

```
Gemini said:

<concise summary of Gemini's final answer>

Relevant details:

<specific facts, caveats, URLs, or reasoning worth preserving>

My read:

<brief assessment, agreement/disagreement, uncertainty, or recommended next step>
```

If the user asked only to fetch Gemini's answer, keep `My read` short.

## Troubleshooting

### Gemini is logged out

Stop and say:

```
Gemini is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

### Human verification / CAPTCHA

Stop and say:

```
Gemini is asking for human verification. Please complete it manually in the browser, then I can continue.
```

### Overlay blocks the page

Dismiss harmless overlays. Do not click upgrade, subscribe, buy, connect account, share, or privacy-sensitive account actions.

### Pro mode is unavailable (quota exhausted)

If `Pro` cannot be enabled, fall back to `Thinking`. If `Thinking` is also unavailable, stop and ask whether to continue in `Fast` mode.

### Mode picker does not open

Take a new snapshot and verify the UID for the mode picker control. Click it using the UID from the most recent snapshot. If the menu still does not appear after two attempts, stop and ask:

```
I cannot open the mode picker to verify or change the Gemini mode. Would you like me to continue in the current mode, or stop here?
```

### Prompt typed but did not submit

Take a snapshot and click the submit button directly using its UID.

Do not spam submissions.

### Stale text in composer

Correct behavior: clear the textbox in place using `chrome-devtools_fill` with empty string. Do not append to stale text.

### Transient error (e.g. "Something went wrong (1013)")

If a transient error such as `Something went wrong (1013)` appears, do not immediately overwrite the prompt or retry. Wait briefly, take another snapshot, and check whether the answer has appeared or generation resumed before retrying. If retrying, clear the composer first with `chrome-devtools_fill` and an empty string to avoid appending duplicate prompt text.

### Response extraction is messy

Use the Copy button nearest the latest response. This is usually cleaner than parsing all page text.

### Multiple Gemini tabs exist

Prefer the tab already used for this session when the user asks a follow-up. For unrelated questions, open a fresh tab at `https://gemini.google.com/app` and verify the mode before typing.

## Gemini UI terms to know

Typical Gemini web UI elements:

- **Mode/model picker**: Dropdown or toggle for switching between `Fast`, `Pro`, and `Thinking` modes. May show the current mode name or a model label.
- **Prompt composer**: Text input area, often with placeholder text like "Enter a prompt here" or "Ask Gemini".
- **Send/submit button**: Button with accessible name like "Submit", "Send", "Run", or a send/arrow icon.
- **Copy button**: Appears near assistant responses; use for clean extraction.
- **Stop button**: Visible while Gemini is generating a response.
- **Pro**: Preferred mode; may show as "Gemini Pro" or similar in the mode picker.
- **Thinking**: Fallback mode; may show as "Gemini Pro with Thinking" or similar.
- **Fast**: Default mode; should be changed to Pro before submitting.
