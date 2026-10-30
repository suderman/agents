# Working with Jon

Use NixOS and flake-based tools. Do not suggest apt, brew, or imperative
package installs. Use `nix shell` for temporary tools.

Read files before editing. Preserve unrelated changes. Use the smallest change
that solves the requested problem, with standard libraries before dependencies.
Run checks before claiming success and report the commands and results.
Do not commit or push unless asked.

Before substantive work, look for an existing project under `~/org/work/`.
When one exists, load `project-org-tasks`, resume its task, and keep that Org
record current. Do not create repository-local planning files as a substitute.

When writing Org, the file records structure and the editor wraps lines:

- Put each paragraph and each list item on one physical line, however long.
  Never hard-wrap Org prose to a column or run `fill-paragraph` on it.
- Start a heading's content on the next line, whether that is planning, a
  drawer, text, a list, or a child heading. Planning and drawers stay
  directly under their heading.
- End a finished paragraph, list, table, or block with one blank line when
  anything follows it, including the next heading. Put no blank line after a
  heading or drawer, inside a drawer, between ordinary list items, or at the
  end of the file, and never two in a row.
- Keep source, example, and verse blocks, tables, and drawers exactly as
  their syntax and content need.
- Leave text you are not otherwise editing as it is. Never add blank lines
  to change how folded headings look; Emacs handles that.
- In headings, put one space between the title and its tags. Do not pad
  tags to a column.

Use `~/profile/skills` for personal authored skills and `~/profile/prompts` for
personal commands. That collection has no Git history. Ask before editing them.
`~/.agents/skills` combines generated community content with repository skills
linked from the checkouts that own them, such as June's `skills/`. Resolve a
skill's link and edit a repository skill in its owning repository. Change
community selections through `~/.agents/agents skill`, not by editing
downloaded files. Native Claude skills and state remain owned by Claude Code.

Keep secrets out of repositories and logs. Do not edit `/etc/nixos` unless
Jon explicitly requests system changes. Package installation, persistence,
services, and secrets belong to that separate system configuration.

Be direct. Cut filler and praise. Use plain words. Avoid em dashes.
Load `unslop` when writing prose.
