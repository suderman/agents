---
name: copilot-browser
description: Ask Microsoft Copilot questions through the user's logged-in copilot.microsoft.com browser session using chrome-devtools MCP.
---

# Copilot Browser Skill

Use this skill when the user asks you to consult Microsoft Copilot through the browser, ask Copilot a question, get a second opinion from Copilot, compare your answer with Copilot, or retrieve an answer from the user's logged-in Copilot web session.

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

Always enter Copilot through:

```
https://copilot.microsoft.com/
```

New global chats are fine. No project scoping is required.

## Core rules

- Use the user's existing logged-in Copilot browser session.
- If Copilot is not logged in, stop. Ask the user to log in manually and create an active logged-in session, then retry.
- Dismiss overlays, popups, marketing banners, cookie banners, upgrade prompts, onboarding dialogs, and similar interruptions before proceeding.
- Enable `Think deeper` before submitting a prompt. Treat this as a hard gate: do not proceed in `Smart` mode unless the user explicitly approves continuing without Think deeper.
- Submit by clicking Copilot's send button using `chrome-devtools_click` with the UID from a snapshot.
- Ask directly as the user. Do **not** prepend disclosure text like "I am using you as a second-opinion assistant".
- Allow Copilot enough time to generate the answer. This may take 30 seconds to 5 minutes depending on complexity and network speed.
- Do not send secrets, credentials, private keys, tokens, client-private data, or sensitive personal/financial material unless the user explicitly approves that exact prompt.
- Do not pretend Copilot's answer is your own work. Clearly separate what Copilot said from your own assessment.

## Basic workflow

### 1. Check browser availability

Use `chrome-devtools_list_pages` to see open tabs. If no relevant tabs exist, open a new one with `chrome-devtools_new_page`.

If the chrome-devtools connection is unavailable, report the problem directly.

### 2. Open or reuse Copilot

Prefer an existing relevant Copilot tab for follow-up questions.

For unrelated questions, open or navigate to:

```
chrome-devtools_new_page url="https://copilot.microsoft.com/"
```

New global chats are acceptable.

### 3. Dismiss overlays

After page load, take a snapshot:

```
chrome-devtools_take_snapshot
```

Dismiss harmless overlays that block the composer using UIDs from the snapshot. Do not click destructive or account-changing actions. Avoid anything that subscribes, upgrades, purchases, changes account settings, enables sharing, connects accounts, or changes privacy settings.

After each dismissal, take another snapshot. Continue until the prompt composer is reachable or until blocked by login/verification.

### 4. Verify logged-in state

Take a snapshot and inspect the page text.

If the page shows a login/signup state, such as "Sign in", "Log in", "Continue with Microsoft", or "Microsoft account", stop and tell the user:

```
Copilot is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

If Copilot shows human verification, CAPTCHA, unusual activity, or an account prompt requiring the human, stop and ask the user to complete it manually.

### 5. Start or use a chat

New global chats are fine. If Copilot lands on a usable composer, use it directly.

If the composer contains stale draft text, clear it in place before typing using `chrome-devtools_fill` with the textbox UID and an empty string.

### 6. Enable Think deeper

Before submitting, take a snapshot and inspect the composer controls.

Copilot may default to `Smart`, which is the simpler mode. The composer mode toggle button has `aria-label="Smart"` when Smart is active. After switching, the active mode should be `Think deeper`. Do **not** submit while the composer mode button still has `aria-label="Smart"`.

If a `Think deeper` option/control is visible, enable it before submitting. This is a required step, not optional, unless the control cannot be found after inspection.

Likely workflow:

1. Inspect the mode toggle in the snapshot.
2. If the composer mode button has accessible name "Smart", click it using the UID from the snapshot.
3. The mode menu is rendered elsewhere in the DOM; it may not look visually attached to the composer in the snapshot.
4. Wait briefly, then immediately click the Think deeper option by finding it in a new snapshot.
5. Inspect again with a fresh snapshot.
6. Verify the composer mode button now shows "Think deeper", not "Smart".

If snapshot-driven clicks do not open the menu after two attempts, use the bundled direct-CDP fallback script. It connects to Chromium's remote debugging port, finds a Copilot page, and runs JavaScript to click the Smart button and then the Think deeper option.

Run:

```bash
python3 /home/jon/.config/opencode/skills/copilot-browser/scripts/enable_think_deeper.py
```

Expected successful verification includes:

```
verify: [{'label': 'Think deeper', ...}]
```

If `Think deeper` still cannot be enabled or verified after this fallback, stop and ask the user whether to continue in Smart mode. Do not silently proceed in Smart mode.

### 7. Type the prompt

Prepare a concise, self-contained prompt. Type it directly as the user.

Prompt template:

```
<USER_TASK>
```

Use `chrome-devtools_fill` with the composer textbox UID from a snapshot.

### 8. Submit the prompt

Primary submit method: Look for a button with accessible name "Submit message" or "Send" in the snapshot, then click using its UID.

Do not spam submissions. One successful click is sufficient.

### 9. Wait for completion

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

Consider the answer complete when:

- stop/progress indicators disappear
- composer/send control returns
- page text is stable across two polls
- a Copy button appears near the latest assistant message

### 10. Extract the final answer

Prefer the cleanest extraction available.

Best option:

1. Use `chrome-devtools_take_snapshot` to locate the Copy button nearest the latest Copilot response.
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

If clipboard extraction is unavailable, use `chrome-devtools_take_snapshot` and `chrome-devtools_evaluate_script` to read page content, then extract the latest Copilot answer after the submitted prompt. Avoid returning noisy full-page text.

### 11. Return the result

Use:

```
Copilot said:

<concise summary of Copilot's answer>

Relevant details:

<specific facts, commands, caveats, URLs, or reasoning worth preserving>

My read:

<brief assessment, agreement/disagreement, uncertainty, or recommended next step>
```

If the user asked only to fetch Copilot's answer, keep `My read` short.

## Troubleshooting

### Copilot is logged out

Stop and say:

```
Copilot is not logged in in this browser session. Please log in manually and create an active logged-in session, then I can retry.
```

### Human verification / CAPTCHA

Stop and say:

```
Copilot is asking for human verification. Please complete it manually in the browser, then I can continue.
```

### Overlay blocks the page

Dismiss harmless overlays. Do not click upgrade, subscribe, buy, connect account, share, or privacy-sensitive account actions.

### Think deeper unavailable

If Copilot remains in `Smart` mode, do not immediately proceed. First:

1. Take a snapshot and locate the mode toggle button.
2. Click the Smart button using its UID from the snapshot.
3. Wait briefly, then take another snapshot and click the Think deeper option using its UID.
4. Inspect again and verify the mode button now shows "Think deeper".

If the menu still does not open after two snapshot-driven attempts, use the direct-CDP fallback script:

```bash
python3 /home/jon/.config/opencode/skills/copilot-browser/scripts/enable_think_deeper.py
```

If `Think deeper` is unavailable or cannot be verified after this, stop and ask the user whether to continue in Smart mode. Do not silently proceed.

### Prompt typed but did not submit

Take a snapshot and click the submit button directly using its UID.

Do not spam submissions.

### Console noise

These console/network messages are usually not relevant to Copilot mode switching unless the UI is visibly broken:

- blocked Sentry telemetry, e.g. `sentry.io ... ERR_BLOCKED_BY_CLIENT`
- Microsoft Graph profile photo 404, e.g. `/me/photo/$value 404`
- CSP violation reports such as `wasm-eval`

Do not spend time debugging these for normal Copilot chat automation. Focus on visible UI state and whether the Smart / Think deeper buttons can be clicked.
