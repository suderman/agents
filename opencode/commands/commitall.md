---
description: Stage and commit all current changes in logical groups
agent: mini
---

Review all current repository changes and commit them in safe, logical groups.

Use only safe, non-destructive git inspection commands while deciding what to
do:

- `git status`
- `git diff`
- `git diff --stat`
- `git diff -- <path>`
- `git log --oneline -n 5` if recent context is useful

Do not push, tag, reset, clean, checkout, switch branches, rebase, amend
commits, or rewrite history.

Important safety rule:

- Do not use `git reset`, `git commit --amend`, `git rebase`, `git checkout`,
  `git switch`, or `git clean`.
- If you make a bad commit or realize a commit is missing files after it has
  been created, stop and report the problem instead of trying to repair history.
- Do not run interactive commands such as `git add -p` unless the environment
  clearly supports interaction.

Process:

1. Inspect the full working tree with `git status` and `git diff --stat`.
2. Review the actual diffs for every changed file.
3. Decide the smallest sensible set of logical commits.
4. For each commit:
   - stage only the files that belong in that commit
   - if only part of a file belongs in the commit, either use a safe
     non-interactive staging method or leave it uncommitted and explain why
   - run `git status`
   - run `git diff --staged --stat`
   - run `git diff --staged`
   - verify that the staged diff exactly matches the commit message you are
     about to write
   - verify that every file mentioned in the commit message is actually staged
   - verify that no unrelated file or hunk is staged
   - create the commit with a clear, detailed message
   - after the commit, run `git status` again before continuing

Commit-message rules:

- Use an appropriate conventional commit type when it fits naturally, such as
  `fix:`, `feat:`, `style:`, `refactor:`, `docs:`, `chore:`, or `test:`.
- The subject should describe exactly what the staged diff does.
- The body may explain why the change was made or list notable details.
- Do not claim that a commit changes a file, feature, or behavior unless that
  change is actually present in the staged diff.

Do not squash unrelated work into one large commit.

Completion:

After all safe commits are complete, show:

- the commits created, using `git log --oneline -n <number>`
- any remaining uncommitted changes from `git status`
- any skipped files or hunks, with a brief explanation
