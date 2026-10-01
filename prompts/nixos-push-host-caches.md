---
description: Build NixOS host closures and push them to Attic
---

Prepare Attic cache entries for NixOS hosts in the current working project.

Requested hosts or preview request: `$ARGUMENTS`

Follow this workflow:

1. Work from the current project's repository root. Do not switch to another
   repository or guess an absolute project path.
2. Read the current project's `AGENTS.md` if present.
3. Require and read `.agents/skills/build-push-hosts/SKILL.md` before running any
   build or cache command. If it is absent, stop and explain that this prompt
   must be run from the appropriate NixOS repository.
4. Follow that skill exactly. It owns the build, cache, timeout, and safety rules.
5. Use `nix develop` and the deterministic `nixos cache` command as specified
   by the skill. Pass through the requested hosts. Do not pass preview wording
   as a host argument.
6. If no hosts were supplied, preserve `nixos cache` interactive host selection.
7. If the invocation or user request clearly asks for a preview, use `--dry-run`
   instead of building or pushing.
8. Report the cache used, hosts processed, dry-run versus real push, and any
   failures with the first failing command.
