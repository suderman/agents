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

Use `~/profile/skills` for personal authored skills and `~/profile/prompts` for
personal commands. Ask before editing them. `~/.agents/skills` is generated
community content. Change its selections through `~/.agents/agents skill`,
not by editing downloaded files. Native Claude skills and state remain owned
by Claude Code.

Keep secrets out of repositories and logs. Do not edit `/etc/nixos` unless
Jon explicitly requests system changes. Package installation, persistence,
services, and secrets belong to that separate system configuration.

Be direct. Cut filler and praise. Use plain words. Avoid em dashes.
Load `unslop` when writing prose.
