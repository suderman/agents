---
name: perplexity-browser
description: Ask Perplexity questions through the user's logged-in perplexity.ai browser session using chrome-devtools MCP.
---

# Perplexity Browser Skill

Use this skill when the user asks you to consult Perplexity, ask Perplexity a question, get a sourced web answer, or retrieve an answer from the user's logged-in Perplexity browser session.

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

Always enter Perplexity through:

```
https://www.perplexity.ai/
```

Use the main Perplexity home/search page. Do not use Spaces by default.

## Core rules

- Use the user's existing logged-in Perplexity browser session.
- If Perplexity is not logged in, stop. Ask the user to log in manually and create an active logged-in session, then retry.
- Dismiss overlays, popups, cookie banners, onboarding dialogs, upgrade prompts, and similar interruptions before proceeding.
- Default Perplexity mode is fine. Do not try to change model/search mode unless the user asks.
- Ask directly as the user. Do **not** prepend disclosure text like "I am using you as a second-opinion assistant".
- Preserve the user's exact question unless minimal context is needed to make it self-contained.
- Do not send secrets, credentials, private keys, tokens, client-private data, or sensitive personal/financial material unless the user explicitly approves that exact prompt.
- Do not pretend Perplexity's answer is your own work. Clearly separate what Perplexity said from your own assessment.
- Perplexity answers may cite sources. Preserve important citations/source names when summarizing.

## Basic workflow

### 1. Check browser availability

Use `chrome-devtools_list_pages` to see open tabs. If no relevant tabs exist, open a new one with `chrome-devtools_new_page`.

If the chrome-devtools connection is unavailable, report the problem directly.

### 2. Open or reuse Perplexity

Prefer an existing relevant Perplexity tab for follow-up questions.

For unrelated questions, open or navigate to:

```
chrome-devtools_new_page url="https://www.perplexity.ai/"
```

### 3. Dismiss overlays

After page load, take a snapshot:

```
chrome-devtools_take_snapshot
```

Dismiss harmless overlays that block the page or composer using UIDs from the snapshot. Do not click destructive or account-changing actions. Avoid anything that subscribes, upgrades, purchases, changes account settings, enables sharing, connects accounts, or changes privacy settings.

### 4. Verify logged-in state

Take a snapshot and inspect the page text.

If the page shows login/signup state, such as "Sign in", "Log in", "Continue with Google", "Continue with Apple", or "Continue with email", stop and tell the user:

```
Perplexity is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

If Perplexity shows human verification, CAPTCHA, unusual activity, or an account prompt requiring the human, stop and ask the user to complete it manually.

### 5. Use the main Perplexity composer

By default, use the main Perplexity home/search composer at `https://www.perplexity.ai/`.

Workflow:

1. Navigate to `https://www.perplexity.ai/`.
2. Use the main textbox, usually labeled or placeholdered like "Ask anything...".
3. Ignore Spaces and any `Computer`/task-oriented Space UI unless the user explicitly asks for it.

Do not navigate to `/spaces` or open the `opencode` Space by default. It can expose a task/computer UI and confuse the flow.

Do not open unrelated existing threads for unrelated questions just because a draft exists. Clear stale drafts in place.

Before typing, clear stale composer text using `chrome-devtools_fill` with the textbox UID and an empty string.

### 6. Type the prompt

Prepare a concise, self-contained prompt. Type it directly as the user.

Prompt template:

```
<USER_TASK>
```

Use `chrome-devtools_fill` with the composer textbox UID from a snapshot.

### 7. Submit the prompt

The submit button has `aria-label="Submit"`, but it may not exist until after text has been successfully entered into the textbox. Do not look for or click submit before typing.

After typing, verify the typed prompt appears in the composer or page text if possible, then take a snapshot and click the submit button using its UID.

If the visible submit button has a different accessible name, use the exact name from the snapshot.

If `button[aria-label="Submit"]` is not found after typing, the text may not have entered the real composer. Re-inspect with a fresh snapshot, retry typing into the textbox UID, then try other composer elements.

If the UI remains difficult, a reliable fallback is to navigate directly to a Perplexity search URL:

```
https://www.perplexity.ai/search?q=<URL_ENCODED_QUERY>&source=web
```

Do not spam submissions. One successful click is sufficient.

### 8. Wait for completion

Allow 30 seconds to 5 minutes.

Poll periodically by taking snapshots:

```
chrome-devtools_take_snapshot
```

The response is probably still streaming if:

- a Stop button is visible
- response text is still changing
- spinner/progress indicator is visible
- composer is disabled
- send button has not returned

Consider the answer complete when:

- stop/progress indicators disappear
- composer/send control returns
- page text is stable across two polls
- source/citation cards have loaded, if present

### 9. Extract the final answer

Prefer the cleanest extraction available.

Best option:

1. Use `chrome-devtools_take_snapshot` to locate the Copy button nearest the latest Perplexity answer.
2. Click that Copy button using its UID.
3. Read clipboard with shell if available:

```bash
wl-paste
```

Fallbacks:

```bash
xclip -selection clipboard -o
xsel -b
```

If clipboard extraction is unavailable, use `chrome-devtools_take_snapshot` and `chrome-devtools_evaluate_script` to read page content, then extract the latest Perplexity answer after the submitted prompt. Avoid returning noisy full-page text.

Preserve source names/URLs when useful.

### 10. Return the result

Use:

```
Perplexity said:

<concise summary of Perplexity's answer>

Relevant sources:

- <source name / URL if available>

My read:

<brief assessment, uncertainty, or recommended next step>
```

If the user asked only to fetch Perplexity's answer, keep `My read` short.

## Troubleshooting

### Perplexity is logged out

Stop and say:

```
Perplexity is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

### Human verification / CAPTCHA

Stop and say:

```
Perplexity is asking for human verification. Please complete it manually in the browser, then I can continue.
```

### Overlay blocks the page

Dismiss harmless overlays. Do not click upgrade, subscribe, buy, connect account, share, or privacy-sensitive account actions.

### Prompt typed but did not submit

Take a snapshot, identify the exact visible submit/send button UID, then click it once.

Known behavior: Perplexity's submit button appears as `button[aria-label="Submit"]` only after text is entered.

If submit is still not visible after typing, retry typing into the real composer. If that still fails, use direct search URL fallback:

```
https://www.perplexity.ai/search?q=<URL_ENCODED_QUERY>&source=web
```

### Stale text in composer

Correct behavior: clear the textbox in place using `chrome-devtools_fill` with empty string. Do not append to stale text.

### Response extraction is messy

Use the Copy button nearest the latest response. This is usually cleaner than parsing all page text.
