---
description: Commit staged git changes only
---

Commit exactly the changes that are already staged.

Scope rules:

- Do not edit, format, generate, delete, stage, or unstage files.
- Do not run `git add`, `git restore`, `git reset`, `git checkout`, `git switch`, `git clean`, `git commit --amend`, `git rebase`, `git push`, or `git tag`.
- Use only safe inspection before committing: `git status`, `git diff --staged --stat`, `git diff --staged`, `git diff --stat`, and optionally `git log --oneline -n 5`.

Process:

1. Run `git status`.
2. Stop if no staged changes exist. Do not stage anything.
3. Inspect `git diff --staged --stat`.
4. Inspect full `git diff --staged`.
5. Optionally inspect `git diff --stat` to know what remains unstaged, but do not describe unstaged work as committed.
6. Write one commit message that matches only staged diff.
7. Before committing, verify:
   - every file or behavior named in message appears in staged diff
   - no unstaged or unrelated work is described
   - message does not mention future work, skipped work, or verification not run
8. Create exactly one commit.

Message rules:

- Prefer conventional subject when natural: `fix:`, `feat:`, `style:`, `refactor:`, `docs:`, `chore:`, or `test:`.
- Keep subject specific to staged diff.
- Add body only when useful: multiple notable details, non-obvious reason, or important constraint.
- Do not exaggerate scope.

Stop without committing if staged diff looks incomplete, inconsistent, generated accidentally, unsafe, or impossible to describe honestly. Report exact issue and what user should stage or fix.

After commit, show:

- new commit via `git log --oneline -n 1`
- repository state via `git status`
- whether unstaged changes remain
