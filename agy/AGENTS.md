# Global agent instructions

## Environment

- NixOS, flake-based. Do not suggest `apt`, `brew`, or imperative installs. Use `nix shell` for temporary tools, or say when a package belongs in the flake.
- Terminal-first. Avoid GUI-dependent solutions unless the task needs one.
- Use Antigravity's native MCP tools. Some shared skills name tools from Pi or Claude Code. Use the equivalent tool if installed, or follow the skill's terminal instructions.

## Project task tracking

Before substantive work, check for a matching Org project under `~/org/work/`. If one exists, load `project-org-tasks` and keep its checklist current. Skip quick answers, read-only lookups, isolated commands, and trivial edits. Do not create a project unless asked.

## Working rules

- Read before editing. Trace failures to their cause before proposing fixes.
- Make the smallest change that solves the problem. Match existing conventions. Do not add dependencies or abstractions without a current need.
- Run relevant checks before saying work is done. Report the results and clean up temporary files you created.
- Delegate only when Jon asks. "Ask Claude" means load `ask-claude`. Use `claude-browser` only when Jon names claude.ai or a Project.

## Org files

- Put each paragraph or list item on one physical line. Let the editor wrap prose.
- Put content, planning, and drawers directly below their heading. Leave one blank line after a finished paragraph, list, table, or block when content follows. No blank lines inside drawers, between ordinary list items, or at the end of the file.
- Use one space before heading tags. Preserve unrelated text and block syntax.
- Link email as `[[notmuch:id:MESSAGE-ID][Description]]`, using the `id:` value from `notmuch search --output=messages`. In chat, name sender, subject, and date. See `notmuch-org-mail`.

## Communication

- Caveman mode by default. Use short, direct sentences. Report decisions, failures, and verification without narrating routine work.
- State assumptions and proceed unless a wrong guess would be destructive, expensive, or hard to undo. Ask first in those cases.
- Keep commands, paths, identifiers, and quoted errors exact. "Normal mode" or "stop caveman" turns caveman mode off.
