# Agent Rules and Engineering Conventions

## Purpose

This document defines baseline conventions for agents contributing to a project.

Treat it as a default operating guide. Project-specific documentation, existing
code conventions, and direct user instructions take precedence.

Instruction priority:

1. Direct user instructions
2. Project-specific docs and scripts
3. Existing code conventions
4. This AGENTS.md file
5. Agent defaults

When instructions conflict, follow the higher-priority source and briefly note
the conflict if it affects the result.

---

## Core principles

- Complexity is the primary enemy.
- Write code for humans first.
- Prefer simple, clear, maintainable solutions over clever or abstract ones.
- Prefer explicit behavior over implicit assumptions.
- Prefer boring, well-understood solutions unless novelty is explicitly
  required.
- Prefer reversible, incremental changes over large rewrites.
- Avoid premature optimization.
- Treat warnings and errors as bugs, not noise.
- Preserve the principle of least surprise: code should behave as a reasonable
  maintainer would expect.

---

## Decision and permission model

- If uncertainty materially affects architecture, security, data integrity,
  public APIs, destructive operations, or user-visible behavior, ask for
  clarification.
- Otherwise, proceed with the smallest safe and reversible change.
- Prefer incremental changes over broad refactors unless explicitly requested.
- If progress would otherwise stall, make the smallest meaningful forward change
  and state assumptions clearly.
- Do not stop at a plan unless the user explicitly asked for planning only.

---

## Worktree hygiene

Before making changes:

- Inspect the current repository state when relevant.
- Be careful not to overwrite unrelated user changes.
- Treat pre-existing modifications as user-owned unless clearly produced by the
  current task.
- Do not clean, reset, switch branches, rewrite history, delete files, or
  discard changes unless explicitly instructed.

After making changes:

- Review the relevant diff.
- Keep the diff scoped to the task.
- Mention unrelated pre-existing changes if they affect verification or safety.

---

## Problem framing before implementation

For non-trivial changes, briefly identify the objective and constraints before
editing when doing so improves safety or clarity.

Prefer this framing:

- What needs to change
- Where the relevant code likely lives
- What must not change
- How the result will be verified

Avoid lengthy planning when the next safe action is obvious.

Separate required work from incidental details and nice-to-haves. Solve the
smallest meaningful subproblem first. Do not solve problems that were not asked
for.

---

## Project task tracking

For substantive repository work, check whether the repository maps to an
existing Org project under `~/org/work/`.

- When an existing project is available, load the `project-org-tasks` skill and
  use its Org project file as the persistent task and progress record.
- Prefer the existing Org task thread over creating a separate plan, TODO file,
  checklist document, or repository-local work log.
- Resume a matching existing task when possible rather than creating a duplicate.
- Keep the Org task synchronized as meaningful work progresses and before the
  final report.
- Do not create a new Org project merely because work is happening in a
  repository. If no project mapping exists, continue normally unless the user
  asks to establish one.
- Do not treat repository-local `work/`, TODO, or planning files as substitutes
  for the Org project system unless the repository explicitly defines them as
  part of its own workflow.

---

## Change discipline

- Prefer minimal diffs over broad rewrites.
- Do not refactor unrelated code unless explicitly requested.
- Preserve existing project conventions unless explicitly instructed to change
  them.
- When multiple solutions exist, choose the simplest viable one.
- Explain reasoning briefly before non-trivial or risky changes.
- Avoid introducing new dependencies unless clearly justified.
- Prefer existing project utilities, standard library features, and established
  libraries over new abstractions.
- Do not perform speculative cleanup, renaming, formatting, or restructuring
  unless necessary to complete the task.
- Avoid changing public APIs, data schemas, migrations, deployment behavior, or
  security-sensitive paths unless required by the task.

---

## Verification and debugging

- When fixing a bug, reproduce or clearly identify the failure before changing
  code when feasible.
- Base fixes on evidence, not guesses.
- After making a change, verify the requested behavior in the most relevant real
  execution path available.
- Use the narrowest useful test, build, lint, typecheck, or runtime check.
- Do not assume a change is correct merely because it compiles or looks
  reasonable.
- Check nearby behavior for obvious regressions when practical.
- If validation fails, distinguish between task-related failures and
  pre-existing or unrelated failures.
- Do not chase unrelated failures indefinitely. Report them clearly and stop
  when the requested work has been responsibly verified or bounded.

---

## Tool usage

- Prefer repository context, existing project documentation, and nearby code
  before fetching external references.
- Do not fetch external documentation unnecessarily when the answer is already
  clear from project context.
- Use Context7 when working with unfamiliar libraries, APIs, frameworks, or
  unclear documentation.
- Use Context7 to resolve `libraryId` and retrieve documentation when needed.
- Use `gh_grep` when official documentation is insufficient, ambiguous, stale,
  or incomplete.
- Prefer direct evidence from code, tests, logs, and docs over assumptions.
- Load the `web-inspector-editing` skill when testing temporary CSS or
  JavaScript changes on a live website through chrome-devtools.
- When using browser-side CSS or JS experiments, reload between attempts so each
  test starts from a clean page state.

---

## Browser control basics

In this environment, `chrome-devtools` MCP may be unavailable or disconnected
even when Chromium is running and reachable over CDP.

Local browser launcher:

- Browser control expects Chromium to be launched through the `chromium-agent`
  wrapper.
- Do not launch arbitrary `chromium`, `google-chrome`, or a fresh browser
  profile for agent-controlled browser work unless the user explicitly asks.
- Before using chrome-devtools MCP or direct CDP fallback, verify that the
  `chromium-agent` browser is running and reachable.
- If browser control fails, first check whether the expected `chromium-agent`
  instance is running before debugging MCP itself.

Rules:

- If the user asks for browser automation or inspection, you may proceed even if
  the MCP server is unavailable.
- Treat MCP availability and browser controllability as separate concerns.
- If MCP is unavailable, direct CDP fallback is allowed when possible.
- Do not assume opening a URL proves browser control; verify with an actual
  inspection or browser action.
- Briefly state which path you used: MCP or direct CDP fallback.

---

## Commit message conventions

Follow Conventional Commits unless the project defines its own rules.

Guidelines:

- Use the imperative mood.
- Use lowercase in the summary line.
- Do not end the summary with a period.
- Keep the summary concise and ideally under 72 characters.
- Use plain ASCII characters in commit messages.
- Add a body when rationale, tradeoffs, or consequences are not obvious.

Examples:

```text
docs: correct spelling of changelog
```

```text
feat(lang): add polish language
```

```text
fix: prevent request race conditions

Introduce request ids and track the latest request. Ignore responses from
outdated requests.

Remove timeouts that previously masked the issue.

Reviewed-by: Z
Refs: #123
```

---

## Security considerations

- Never log sensitive data, including credentials, secrets, tokens, or PII.
- Treat all external input as untrusted until validated.
- Validate data for correctness, not merely absence of errors.
- Avoid adding new dependencies when existing libraries or the standard library
  are sufficient.
- Do not assume code is secure without explicit reasoning.
- Do not destroy or mutate data unless it has been explicitly verified as safe
  to discard.
- Use assertions where appropriate and supported, but do not rely on them as a
  substitute for real validation.
- Be cautious with filesystem, shell, network, auth, payment, deployment, and
  migration code.

---

## Default engineering bias

- Prefer clarity over cleverness.
- Prefer local reasoning over global abstraction.
- Prefer explicitness over magic.
- Prefer maintainability over micro-optimizations.
- Prefer small, understandable changes over sweeping redesigns.
- Prefer boring code that works over impressive code that needs explanation.
