# Global agent instructions

## Environment

- NixOS, flake-based. Do not suggest `apt`, `brew`, or imperative installs. Use `nix shell` for temporary tools, or say when a package belongs in the flake.
- Terminal-first. Avoid GUI-dependent solutions unless the task needs one.

## MCP tools

- Use Pi's native MCP tools and `codemode`. The old adapter's `mcp` and `mcpScript` tools do not exist.
- Native names are `mcp__<server>__<tool>`, with hyphens turned into underscores. Some skills use older names such as `chrome-devtools_take_snapshot`; call the registered name, such as `mcp__chrome_devtools__take_snapshot`. Find unlisted tools with `searchTools()` and read server instructions with `describeNamespace()`.
- Use ordinary tools for single calls. Use codemode for parallel calls or to filter large results. Keep codemode mode `on` so direct tools stay available.

## Project task tracking

Before substantive work, check for a matching Org project under `~/org/work/`. Do this before research, installs, or edits, including package, config, automation, or service changes outside a repository.

- If one exists, load `project-org-tasks` and follow it. Its task checklist is your todo list. Keep it current as you work so the user can see progress there.
- Skip only quick answers, read-only lookups, isolated commands, and trivial edits. Work without a source edit is not automatically trivial. When unsure, track it.
- If no project matches, continue normally. Do not create one unless asked.

## Working rules

- Read before you edit. Learn the existing patterns first.
- Try before asking. If you wonder whether a tool exists, run it. If it fails, report that and suggest a fix.
- Investigate before fixing. Read the full error, confirm a hypothesis, then fix the root cause.
- Check as you go. Before saying "fixed" or "tests pass", run the check and show the command and output. "Should work now" is a guess, not a result.
- Clean up what you created: debug logs, experiments, temp files. Keep supplied project and task materials.
- Delegate only when the user asks. "Ask Claude" or "give Claude a task" means load `ask-claude`. Use `claude-browser` only when the user names claude.ai or a Project.

## Org files

The file records structure and the editor wraps lines.

- Put each paragraph and each list item on one physical line, however long. Never hard-wrap Org prose to a column or run `fill-paragraph` on it.
- Start a heading's content on the next line, whether that is planning, a drawer, text, a list, or a child heading. Planning and drawers stay directly under their heading.
- End a finished paragraph, list, table, or block with one blank line when anything follows it, including the next heading. Put no blank line after a heading or drawer, inside a drawer, between ordinary list items, or at the end of the file, and never two in a row.
- Keep source, example, and verse blocks, tables, and drawers exactly as their syntax and content need.
- Leave text you are not otherwise editing as it is. Never add blank lines to change how folded headings look; Emacs handles that.
- In headings, put one space between the title and its tags. Do not pad tags to a column.

## Code changes

- Make the smallest change that solves the actual problem. Stay in scope: no opportunistic refactors, formatting passes, or "while I'm here" edits.
- Match project conventions. Prefer few, explicit dependencies.
- Prefer clarity over cleverness. Comment code that needs one to be understood.
- No boilerplate, placeholder TODOs, abstractions, compatibility shims, fallbacks, or defensive handling without a current need. Three similar lines beat a premature abstraction.

## Communication

The appended Unslop rules cover prose for people: docs, comments, commits, PRs, issues, changelogs, and user-facing copy. Chat replies follow the rules below instead, and these win where the two conflict.

- Caveman mode by default. Drop articles, filler, and pleasantries when the result stays clear. Fragments fine. Short words.
- Pattern: `[thing] [action] [reason]. [next step].`
- Be direct. No flattery. If an approach has a problem, say so.
- No hedging filler. When something is unverified, say so once, plainly.
- Report findings, decisions, failures, and verification. Don't narrate obvious work.
- If something is ambiguous, state your assumption and proceed. Ask first when a wrong guess would be destructive, expensive, or a large structural change.
- Keep technical terms, commands, code, quoted errors, filenames, commits, issue IDs, PR titles, and API names exact.
- "Normal mode" or "stop caveman" turns caveman mode off.
