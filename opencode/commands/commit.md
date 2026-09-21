---
description: Commit the currently staged changes
agent: mini
---

Commit the currently staged changes only.

Do not stage, unstage, edit, format, generate, delete, or modify any files.

Do not use:

- `git add`
- `git restore`
- `git reset`
- `git checkout`
- `git switch`
- `git clean`
- `git commit --amend`
- `git rebase`
- formatters
- fixers
- code generators

Use safe read-only inspection commands only:

- `git status`
- `git diff --staged`
- `git diff --staged --stat`
- `git diff --stat`
- `git log --oneline -n 5` if recent context is useful

Process:

1. Run `git status`.
2. Confirm that staged changes exist.
3. Inspect the staged diff carefully with `git diff --staged --stat`.
4. Inspect the full staged diff with `git diff --staged`.
5. Optionally inspect unstaged changes with `git diff --stat`, but do not
   include them in the commit message unless needed to say they were
   intentionally left uncommitted.
6. Write exactly one commit message that accurately describes only what is in
   the staged diff.
7. Verify before committing:
   - every file mentioned in the commit message is staged
   - every behavior claimed in the commit message appears in the staged diff
   - no unstaged or unrelated work is described as committed
   - the commit message does not mention future work, skipped work, or files not
     present in the staged diff
8. Create exactly one commit from the staged changes.

Commit-message rules:

- Use an appropriate conventional commit type when it fits naturally, such as
  `fix:`, `feat:`, `style:`, `refactor:`, `docs:`, `chore:`, or `test:`.
- The subject should describe exactly what the staged diff does.
- Use a body when the staged diff has multiple notable details or when the
  reason for the change is not obvious.
- Do not exaggerate the scope of the change.
- Do not claim verification unless verification was actually run and is relevant
  to the staged diff.

If there are no staged changes:

- do not stage anything
- do not commit
- report that there are no staged changes

If the staged diff looks incomplete, inconsistent, or unsafe to commit as-is:

- do not stage or unstage anything
- do not try to repair it
- do not commit
- explain exactly what looks wrong and what the user should stage or unstage

Completion:

After committing, show:

- the commit created, using `git log --oneline -n 1`
- current repository state from `git status`
- whether any unstaged changes remain
