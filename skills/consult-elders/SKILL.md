---
name: consult-elders
description: Ask Claude, ChatGPT, Copilot, Perplexity, and Gemini the same question through their logged-in browser sessions using chrome-devtools MCP, wait for answers, then synthesize a combined answer.
---

# Skill: Consult Elders

Use this skill when the user asks to "consult the elders", ask multiple web assistants, get external opinions, compare model answers, or synthesize answers from Claude, ChatGPT, Copilot, Perplexity, and Gemini.

## Goal

Ask the same user question to all available elders simultaneously and return a synthesized answer. The goal is to get answers from every provider, but the workflow is best-effort: a failed session, service outage, CAPTCHA, login failure, or offline site for one elder does not block the rest. Each elder has an independent status:

- **answered**: response received and extracted
- **skipped**: user chose to skip or no logged-in session available
- **failed**: error occurred before or after submission (with reason noted)
- **pending**: timeout reached but partial content may exist

Providers:

- Claude, inside the Claude `opencode` project
- ChatGPT, inside the ChatGPT `opencode` project
- Copilot, in a new/global Copilot chat with Think deeper enabled
- Perplexity, from the main Perplexity home/search page
- Gemini, at `https://gemini.google.com/app` (logged-in session)

## Browser control

Use chrome-devtools MCP tools as the primary control path for all providers. Work from the latest snapshot and use UID values from that snapshot.

- Use `chrome-devtools_list_pages`, `chrome-devtools_select_page`, `chrome-devtools_new_page`, `chrome-devtools_navigate_page` for tab/page setup.
- Use `chrome-devtools_take_snapshot` for DOM/accessibility inspection.
- Use `chrome-devtools_click uid="..."` with snapshot UIDs for clicks.
- Use `chrome-devtools_fill uid="..."` with snapshot UIDs for text inputs.
- Use `chrome-devtools_evaluate_script` only when snapshot/click/fill cannot perform a stable action or for reading structured page state.
- Use `chrome-devtools_wait_for` or repeated snapshots for waiting.
- Use `chrome-devtools_press_key` only as a fallback when no send button is available.

## Core rules

- Use the user's existing logged-in browser sessions.
- Do not send secrets, credentials, private keys, tokens, client-private data, or sensitive personal/financial information unless the user explicitly approves that exact prompt.
- Ask all sites the same prompt, typed directly as the user. Do **not** prepend disclosure text like "I am using you as a second-opinion assistant".
- Keep Claude and ChatGPT inside their respective `opencode` projects. Copilot, Perplexity, and Gemini do not need project scoping.
- Do not decide project membership from URL alone. Verify visible project context.
- If any site is logged out, blocked by CAPTCHA, or requires human verification, record the failure reason and continue with other elders.
- Never let one bad session block the rest. If an elder fails before submission, record the reason and move on. If an elder fails after submission or times out, record the reason and use any partial answer only if it is clearly available.
- Do not spend more than a reasonable per-provider budget trying to repair one site; move on after a few attempts.
- If all fail, report all failure reasons and ask whether to retry later.

## Related skills

This skill combines the operational rules from:

- `claude-browser`
- `chatgpt-browser`
- `copilot-browser`
- `perplexity-browser`
- `gemini-browser`

When in doubt about a site-specific detail, follow that site's dedicated skill.

## Prompt handling

Use the user's question directly.

Good prompt:

```
<USER_QUESTION>
```

Do not use:

```
I am using you as a second-opinion assistant...
Task: ...
```

For code review or answer comparison, rewrite only enough to make the request self-contained while still sounding like Jon asked it directly.

## Browser setup

Use `chrome-devtools_list_pages` to see open tabs. Open new tabs with `chrome-devtools_new_page` when needed.

## Claude flow

Preferred project entry:

1. Navigate to `https://claude.ai/projects`.
2. Click the project named `opencode` using the UID from a snapshot.
3. Verify project context is visible, such as `opencode`, "Memory", "Instructions", "Files", "Project content".
4. Use the large rounded composer on the project page directly.
5. If it contains stale draft text such as `hello`, clear it in place using `chrome-devtools_fill` with empty string. Do not click `New chat`, do not navigate to `/new`, and do not open an existing project chat for an unrelated question.
6. Type the prompt with `chrome-devtools_fill` using the textbox UID.
7. Submit with `chrome-devtools_click` using the send button UID.
8. Wait until Claude finishes streaming.

Claude red flags:

- `https://claude.ai/new`
- generic home composer text like `Good afternoon, Jon` / `How can I help you today?` without visible `opencode` project context
- clicking global/sidebar `New chat` after entering the project

If a red flag appears, navigate back to `https://claude.ai/projects`, click `opencode`, verify context, and use the project composer.

## ChatGPT flow

Preferred project entry:

1. Navigate to `https://chatgpt.com/`.
2. Find and click the project named `opencode` in the sidebar using the UID from a snapshot.
3. Verify visible project context shows `opencode`.
4. Use the project-scoped composer/chat controls from there.
5. If the composer contains stale draft text, clear it in place. Do not open unrelated existing chats as a workaround.
6. Type the prompt with `chrome-devtools_fill` using the textbox UID.
7. Submit with `chrome-devtools_click` using the send button UID (look for "Send prompt" or "Send").
8. Wait until ChatGPT finishes streaming.

ChatGPT red flags:

- project context `opencode` is no longer visible
- opening an unrelated existing chat from recents
- using `chrome-devtools_press_key` to submit when a send button is available

## Copilot flow

Preferred entry:

1. Navigate to `https://copilot.microsoft.com/`.
2. Verify logged-in state. Logged-in page usually shows account information such as `Jon` / `Microsoft 365 Family`.
3. Use the visible Copilot composer. New global chats are fine.
4. Enable `Think deeper` before submitting.

Think deeper requirement:

- Copilot defaults to `Smart` mode.
- Try snapshot-driven clicks first to click the Smart button and then the Think deeper option.
- If clicking does not open the menu, use the bundled direct-CDP fallback script:

```bash
python3 /home/jon/.config/opencode/skills/copilot-browser/scripts/enable_think_deeper.py
```

Expected successful verification includes:

```
verify: [{'label': 'Think deeper', ...}]
```

If Think deeper cannot be enabled or verified, ask the user whether to continue in Smart mode. Do not silently proceed in Smart mode.

Type the prompt with `chrome-devtools_fill` using the textbox UID.

Submit with `chrome-devtools_click` using the submit button UID (look for "Submit message" or "Send").

Copilot red flags:

- staying in `Smart` mode without user approval
- using repeated Enter/keypress attempts instead of the submit button
- spending time debugging blocked Sentry/profile-photo/CSP console noise

## Perplexity flow

Preferred entry:

1. Navigate to `https://www.perplexity.ai/`.
2. Verify logged-in state if possible.
3. Use the main Perplexity home/search composer. Do **not** use Spaces by default.
4. Default mode is fine; do not change model/search mode unless the user asks.

Type the prompt with `chrome-devtools_fill` using the textbox UID.

Submit behavior:

- Perplexity's submit button has `aria-label="Submit"`.
- It may not exist until after text is entered.

After typing, submit with `chrome-devtools_click` using the submit button UID.

If submit is not found after typing, use the direct search URL fallback:

```
https://www.perplexity.ai/search?q=<URL_ENCODED_QUERY>&source=web
```

Perplexity red flags:

- navigating to `/spaces` by default
- opening the `opencode` Space by default
- getting distracted by `Computer` / task Space UI
- repeated Enter or keypress attempts

## Gemini flow

Preferred entry:

1. Navigate to `https://gemini.google.com/app` (no trailing slash).
2. Verify logged-in state; a logged-in session shows the user's account or avatar.
3. Select mode before submitting:
   - Default/available mode is `Fast`.
   - If `Pro` is available, prefer it.
   - If `Pro` quota is unavailable or exhausted, fall back to `Thinking` mode.
   - If neither `Pro` nor `Thinking` can be verified as available, mark Gemini as failed/skipped unless the user explicitly approves the current mode.
4. Type the prompt with `chrome-devtools_fill` using the textbox UID.
5. Submit with `chrome-devtools_click` using the submit button UID.
6. After submission, if an `Answer now` confirmation prompt appears, confirm with `chrome-devtools_click` using its UID.
7. Wait until Gemini finishes streaming.

Extraction guard:

- After copying, validate that the clipboard content does not look like a URL or noisy page artifact.
- If the copy returns only a URL or clearly noisy content, try `chrome-devtools_evaluate_script` to read the answer directly from the DOM instead.

Gemini red flags:

- using the Gemini app URL with a trailing slash; use `https://gemini.google.com/app` exactly
- unable to verify Pro or Thinking mode availability
- copy returning a URL instead of the answer
- `Answer now` button not confirmed after submission

## Waiting for answers

After submitting to each site, wait and poll periodically by taking snapshots:

```
chrome-devtools_take_snapshot
```

Streaming indicators may include:

- visible `Stop` control
- response text still changing
- spinner/progress indicator
- disabled composer
- send button not returned

Consider a response complete when:

- stop/progress indicators disappear
- composer/send control returns
- page text is stable across two polls
- a Copy button appears near the latest assistant message

Wait up to about 5 minutes per site for complex questions.

## Extraction

Prefer the cleanest extraction available.

Best option:

1. Use `chrome-devtools_take_snapshot` to locate the Copy button nearest the latest assistant response.
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

If clipboard extraction is unavailable or returns noisy content (see Gemini flow), use `chrome-devtools_take_snapshot` and `chrome-devtools_evaluate_script` to read page content, then extract the latest assistant answer after the submitted prompt. Avoid returning noisy full-page text.

## Synthesis format

Return a compact synthesis, not raw transcripts. Only include per-provider summaries for successful answers. Failed or skipped providers are documented under Notes / failures.

```
Answered:
- Claude: <key points>
- ChatGPT: <key points>
- Copilot: <key points>
- Perplexity: <key points, including important source names if useful>
- Gemini: <key points>

Agreement:
- <where they align>

Differences:
- <where they disagree or emphasize different things>

Group wisdom / combined answer:
<your concise synthesized answer from the successful answers>

Notes / failures:
- <provider>: <reason> (failed before submission / failed after submission / timeout / skipped)
- <provider>: <reason>
```

If the user asked for only the final result, keep individual elder sections very short and put most value in `Combined answer`.

## Failure handling

Each elder is independent. Record status for every provider:

- **Failed before submission**: login issue, CAPTCHA, navigation error, etc. — record reason, continue with others.
- **Failed after submission or timeout**: response error or no response after budget. Use any partial answer only if clearly available.
- **Skipped**: user requested skip or no logged-in session.

If some elders succeed:

```
Answered: Claude, ChatGPT, Perplexity
Failed: Copilot (CAPTCHA block), Gemini (Pro quota exhausted)

<Successful elder summaries>

My synthesis:
...
```

If all elders fail:

```
All elders failed:

- Claude: <reason>
- ChatGPT: <reason>
- Copilot: <reason>
- Perplexity: <reason>
- Gemini: <reason>

Would you like to retry later after fixing login/verification/browser state?
```
