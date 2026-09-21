---
description: Stage and commit current git changes in logical groups
---

Review current repository changes, then stage and commit them in safe logical groups.

Scope rules:

- You may stage files or hunks that belong in next commit.
- Do not edit, format, generate, delete, or otherwise modify working tree contents.
- Do not push, tag, amend, rebase, reset, restore, checkout, switch branches, clean files, or rewrite history.
- If a commit is wrong after creation, stop and report issue. Do not repair history.
- Avoid interactive commands such as `git add -p` unless current environment clearly supports interaction. Prefer path-based staging; skip partial-file commits when safe non-interactive staging is not practical.

Inspection commands to use before deciding:

- `git status`
- `git status --short`
- `git diff --stat`
- `git diff`
- `git diff -- <path>`
- `git ls-files --others --exclude-standard` for untracked files
- `git log --oneline -n 5` if recent commit style helps

For untracked files, inspect contents before staging. Use Pi `read` for text files, or safe file metadata commands when a file is binary.

Process:

1. Run `git status` and `git diff --stat`.
2. Review actual diffs for every tracked change.
3. Inspect every untracked file that may be committed.
4. Decide smallest sensible set of logical commits. Keep unrelated work separate. Skip unsafe or unclear files instead of guessing.
5. For each planned commit:
   - stage only files or hunks that belong in that commit
   - run `git status`
   - run `git diff --staged --stat`
   - run full `git diff --staged`
   - verify staged diff exactly matches intended commit message
   - verify no unrelated file or hunk is staged
   - create one commit with accurate message
   - run `git status` before continuing

Message rules:

- Prefer conventional subject when natural: `fix:`, `feat:`, `style:`, `refactor:`, `docs:`, `chore:`, or `test:`.
- Subject must describe exactly what staged diff does.
- Body may explain why or list notable details.
- Do not claim verification unless relevant command was actually run.
- Do not describe skipped files or unstaged work as committed.

Stop before committing a group if staging would mix unrelated work, if required partial staging is not safe, or if diff appears incomplete/unsafe. Explain what remains and why.

After all safe commits, show:

- created commits via `git log --oneline -n <count>`
- remaining repository state via `git status`
- skipped files or hunks, with brief reason
