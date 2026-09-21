---
name: project-org-tasks
description: >
  Maintains the user's Org work record for substantive project work. Maps active
  work to a logical project at ~/org/work/<domain>/<project>/<project>.org,
  where a project may reference zero, one, or many repositories. Creates or
  resumes task threads, tracks scope, checklists, follow-ups, verification, and
  TODO state, and uses dated task subdirectories for client-provided files and
  other task-specific working material. Inspects those materials as source
  context without treating them as canonical planning records. Use during
  implementation, debugging, refactoring, actionable reviews, explicit project
  ideas, and other substantive work that should persist across sessions. Skip
  quick informational questions, read-only lookups, isolated commands, and
  trivial edits unless the user asks to track them.
license: MIT
---

# Project Org Tasks

Keep the user's Org project record in step with substantive work. The project
file is the canonical planning record for a logical project or workstream. It
is not a transcript, agent scratchpad, repository README, or substitute for
source control.

A logical project may involve no repository, one repository, or several
repositories. Do not assume that project boundaries and Git repository
boundaries are the same.

## Activation

Use this skill automatically for substantive work associated with an existing
project unless the user opts out. This includes substantive repository work
when the repository belongs to a tracked project.

Keep the skill active through follow-up requests in the same work thread, then
synchronize the project file before the final report.

Skip quick explanations, read-only lookups, isolated commands, and trivial
edits unless the user explicitly asks to track them.

## Work tree model

The user's active working information lives under:

```text
~/org/work/
```

A domain groups related work. For example:

```text
~/org/work/studio/
```

Within a domain:

- Direct child Org files represent client-level information or work.
- Direct child directories represent logical projects or workstreams.
- Each project directory contains a same-named canonical Org project file.
- A project directory may also contain dated task directories holding
  task-specific working material.

Example:

```text
~/org/work/studio/
├── northwind.org
├── atlas/
│   ├── atlas.org
│   └── 2026-09-14-import-product-feed/
└── portal/
    ├── portal.org
    └── 2026-09-20-update-language-selector/
```

Here:

- `northwind.org` is a client-level file.
- `atlas/atlas.org` is a project file.
- `portal/portal.org` is a project file.
- `2026-09-14-import-product-feed/` contains files belonging specifically to
  that task.

Do not confuse a direct child client Org file with a project Org file.

## Non-negotiable model

- One project Org file represents one logical project or workstream, not one
  repository.
- The canonical project path is:

  ```text
  ~/org/work/<domain>/<project>/<project>.org
  ```

- A project may reference zero, one, or many source repositories.
- Several repositories may belong to the same project.
- A repository may support more than one logical project. When that makes the
  correct project ambiguous, use the active request and existing project
  metadata rather than assuming the repository uniquely identifies a project.
- Source repositories retain their real Git hosting namespace. Do not reshape
  `~/src` to mirror clients or Org projects.
- For GitHub-hosted work, preserve the natural source layout:

  ```text
  ~/src/<github-owner-or-org>/<repository>
  ```

- Repository-local `work/` directories are not part of this system. Do not look
  for, create, or use `<repo>/work/` as a task source or destination.
- Every first-level heading in a project file is one task, idea, bug, feature,
  or continuing work thread.
- Never create a broad first-level heading such as "Maintain this project" and
  put unrelated work beneath it.
- Preserve user-written headings and prose. Extend the matching thread instead
  of replacing it or creating a duplicate.
- Track all meaningful work required by the active thread. Split an independent
  follow-up into its own first-level heading. Staging, committing, and pushing
  are not independent project tasks; never create a first-level heading for
  them alone.

## Find the project file

Resolve the logical project before creating or editing a project file.

1. Honor an explicit project file or project directory named by the user.
2. If working inside a directory under `~/org/work/<domain>/<project>/`, use
   that project's same-named Org file.
3. If working in a Git repository, find the nearest enclosing Git root.
4. Search existing project files under `~/org/work/` for repository metadata
   whose local link resolves to that Git root.
5. If exactly one logical project matches, use it.
6. If several projects reference the same repository, choose the project that
   clearly matches the user's current request. Ask only when the active project
   is genuinely ambiguous.
7. If no existing project references the repository, use the repository
   basename as a candidate project name, not as proof that a new project should
   be created.
8. When a repository has the conventional path
   `~/src/<namespace>/<repository>`, an existing
   `~/org/work/<namespace>/<repository>/<repository>.org` is a strong default
   match.
9. Do not insert a client name into the source repository path. For example, a
   project for client Northwind may use:

   ```text
   ~/src/studio/portal
   ~/src/studio/portal-fr
   ```

   even though the client name does not appear in either source path.

10. If no reliable project mapping exists, do not invent a hierarchy merely
    from repository ownership. Ask for the logical project when necessary.

Do not search for legacy repository-local `work/` folders while resolving a
project. Their presence does not identify the canonical project or task record.

Read the existing project file before every edit. If it changed during the
session, preserve and merge the new content. Stop and ask only when concurrent
edits conflict with the same thread.

## Client files

A direct child Org file under a domain represents client-level information or
work:

```text
~/org/work/studio/northwind.org
```

Use a client file for information and tasks that belong to the client generally
rather than to one specific project.

A project may reference its client, but client membership does not determine
the project's filesystem path.

For example:

```text
~/org/work/studio/northwind.org
~/org/work/studio/atlas/atlas.org
~/org/work/studio/portal/portal.org
```

Both Atlas and Portal may belong to Northwind without being nested beneath a
`northwind/` directory.

Do not create, modify, or reorganize a client file merely because a project
belongs to that client. Update client-level information only when the current
work genuinely belongs there or the user asks.

## Create the project preamble

Create a project file only when substantive project work begins, the user asks
to capture an idea, or the logical project has otherwise been clearly
established.

Use this general shape for a project with multiple repositories:

```org
#+TITLE: Portal
#+CATEGORY: portal

Client: [[file:../northwind.org][Northwind]]

Repositories:
- portal: [[file:~/src/studio/portal/][local]] | [[https://github.com/studio/portal][GitHub]]
- portalfr: [[file:~/src/studio/portalfr/][local]] | [[https://github.com/studio/portalfr][GitHub]]
```

For a project with one repository:

```org
#+TITLE: Atlas
#+CATEGORY: atlas

Client: [[file:../northwind.org][Northwind]]

Repositories:
- atlas: [[file:~/src/studio/atlas/][local]] | [[https://github.com/studio/atlas][GitHub]]
```

Apply these rules:

- Use home-relative `file:~/src/...` links for repositories. Do not construct
  long `../../..` paths from the Org work tree.
- Use ordinary relative links for resources within the same Org work hierarchy
  when they are clearer, such as `[[file:../northwind.org][Northwind]]`.
- Repository links must point to the repository's real location under `~/src`;
  never alter that path merely to mirror the client or project hierarchy.
- Read each repository's `origin` remote when available.
- Normalize GitHub SSH and HTTPS remotes to
  `https://github.com/owner/repository` and remove a trailing `.git`.
- Omit a GitHub link when the repository has no GitHub remote. Never fabricate
  one.
- List every repository that is genuinely part of the logical project.
- Do not create duplicate project files for secondary repositories. For
  example, `portal` and `portalfr` belong in one `portal.org` project record
  when they are managed as one workstream.
- Omit the `Repositories` section for a project with no source repositories.
- When a matching client file exists, link to it.
- If the client is known but no client file exists, record the client name only
  when useful. Do not create a client file as a side effect.
- Always add `#+CATEGORY`.
- Use the project slug unchanged when it is clear and at most 10 characters.
  Otherwise choose a recognizable category of at most 10 characters.
- Ask only when no clear short category exists.
- Preserve an existing title, category, client reference, repository links, and
  other file metadata unless they are missing or demonstrably stale.

## Task working directories

A task may have a dated directory beside the project Org file for files that
belong specifically to that ask.

Use this form:

```text
~/org/work/<domain>/<project>/YYYY-MM-DD-<task-slug>/
```

Example:

```text
~/org/work/studio/atlas/
├── atlas.org
└── 2026-09-14-import-product-feed/
    ├── client-email.eml
    ├── product-data.xlsx
    ├── supplied-copy.docx
    ├── screenshot.png
    └── review-notes.org
```

These directories are working-material dropzones. Appropriate contents include:

- client-provided documents
- emails related to the ask
- spreadsheets and data files
- screenshots
- PDFs
- supplied assets
- exports
- task-specific notes
- generated deliverables that do not belong in source control

Apply these rules:

- Use the date the task or ask was first captured, not the current date on every
  later session.
- Use a concise lowercase kebab-case slug derived from the task.
- Reuse an existing task directory for the same thread rather than creating a
  new one per session.
- Create a task directory only when there is material to place in it or the
  user explicitly wants one. Do not create empty directories ceremonially.
- Do not copy repository source into the task directory.
- Do not duplicate files that properly belong in Git.
- Do not move client-provided files into a repository merely because source
  changes are being made there.
- Project-wide material that is not specific to one task should not be forced
  into a dated task directory.
- Do not delete or relocate a task directory merely because its heading becomes
  `DONE`. Archiving and long-term file retention are separate workflows.
- Preserve existing filenames unless renaming materially improves the workflow
  or the user asks.
- Never create or fall back to a repository-local `<repo>/work/` directory.
  Task material belongs under the canonical project directory in `~/org/work/`.

When the project already uses an explicit Org property or link to associate a
task with its directory, preserve and update that convention rather than
inventing a second one.

## Working with task materials

Treat files in a task working directory as source material for the active task.

Before implementing work that depends on supplied material:

1. Inspect the relevant files in the task directory.
2. If a `README.md`, notes file, or other obvious summary already exists, read
   it first, but do not assume it contains everything important.
3. Determine the actual request, constraints, clarifications, and unresolved
   questions from the available source material.
4. Inspect the relevant source repositories and project documentation needed to
   understand the task.
5. Implement the requested work.
6. Verify the result using the project's normal tests, checks, build process,
   or focused manual verification.

Client-provided emails, screenshots, documents, spreadsheets, exports, and
other imported files are inputs. Do not modify them unless the user explicitly
asks.

Do not assume that a summary, task heading, email subject, or README fully
captures the request when original source material is available.

If source materials conflict or leave an important requirement ambiguous,
record or report the conflict instead of silently choosing an interpretation.

Do not create additional planning, status, summary, or README files merely to
document agent activity. The task heading in the canonical project Org file is
the primary planning and status record. Create a separate supporting document
only when it is genuinely useful to the work or the user asks for one.

Task directories may be retained as historical source material, but they are
not the sole home for durable knowledge. When completing a task reveals
information that future work should retain:

- record project-level knowledge in the project Org file;
- record client-level knowledge in the appropriate client Org file when it
  genuinely applies across projects;
- record repository-specific technical knowledge in the repository's normal
  documentation when appropriate.

Promoting durable knowledge does not mean deleting or rewriting the original
task materials. Preserve source material unless the user explicitly asks for
cleanup or modification.

## Task states

Use the user's Org workflow consistently:

- `TODO`: captured but not started.
- `PROG`: active investigation or implementation.
- `EVAL`: implementation is ready but awaits review, acceptance, or external
  validation.
- `HOLD`: blocked by a concrete dependency or decision.
- `DONE`: requested work is complete and verified.

Verification, not a commit or push, is the threshold for `DONE`.

If the user later asks only to stage, commit, or push completed work, do not
reopen the completed task or create a new heading for those Git operations.
Record resulting commit or pull request identifiers in the relevant existing
task threads, even when one Git request covers several tasks. Include a
publication checklist item in an active task only when it is useful to the
larger work.

Do not leave a thread in `PROG` merely because source changes are uncommitted.
Never mark a required unchecked item complete without evidence. If unfinished
work remains, keep the thread open or split independent residual work into a
new first-level task.

## Start or resume work

At the beginning of substantive work:

1. Resolve the logical project and read its project file.
2. Find a semantically matching first-level thread before creating one.
3. If the task is new, add a concise verb-led heading and mark it `PROG`.
4. If a matching `TODO`, `EVAL`, or `HOLD` thread is now active, move it to
   `PROG`.
5. Add a short `Scope` section that states the intended outcome and important
   constraints.
6. Add or update a `Checklist` early enough that the user can see the real work
   unfold.
7. If task-specific client or reference files are involved, find or create the
   matching dated task directory and use it consistently.
8. When a matching task directory already contains source material, inspect the
   relevant material before making implementation decisions.

Example:

```org
* PROG Fix duplicate webhook delivery

** Scope

Prevent retries from applying the same delivery twice without changing the
provider-facing response contract.

** Checklist

- [X] Reproduce the duplicate write and trace its call path.
- [ ] Add idempotency at the shared persistence boundary.
- [ ] Verify first delivery, retry, and concurrent delivery behavior.
```

Do not pad the checklist with routine mechanics such as reading files, invoking
tools, announcing plans, or editing the Org record itself. The checklist should
explain the work, not the agent.

## Multi-repository projects

Treat repository count as an implementation detail of the logical project.

For example, Portal is one project even though implementation occurs in two
repositories:

```text
~/org/work/studio/portal/portal.org

~/src/studio/portal
~/src/studio/portalfr
```

A single task such as:

```org
* PROG Update language selector behaviour
```

may require equivalent changes and verification in both repositories.

For multi-repository work:

- Keep one task thread unless the repositories genuinely represent independent
  pieces of work.
- Make the checklist clear about repository-specific implementation or
  verification when that distinction matters.
- Verify all required repositories before considering the task complete.
- Record relevant commits or pull requests from each repository when useful.
- Do not create `portalfr.org` merely because `portalfr` is a separate Git
  repository.

## Maintain the active thread

- Update the checklist at meaningful transitions rather than after every small
  action.
- Record a decision when its rationale will matter in a later session.
- Add `Context`, `Decisions`, `Verification`, or `Outcome` sections only when
  they contain useful information.
- Add a dated `Session YYYY-MM-DD` section only for multi-session work,
  handoffs, or chronology that materially helps continuation.
- Capture a newly discovered task as a separate first-level `TODO` when it is
  not required to finish the current thread.
- Keep failed hypotheses only when they prevent likely repetition.
- Do not turn the project file into a debugging log.
- Keep paths, command names, issue links, pull requests, and commit hashes when
  they make the thread easier to resume.
- Refer to task working files instead of unnecessarily transcribing their full
  contents into the project record.
- Preserve useful distinctions between what the user or client supplied, what
  the agent inferred, and what was verified in the repository.
- Never put credentials, tokens, private keys, secret command output, or other
  secrets into the project file.

Manually added ideas are first-class input. When the user starts one, retain
their wording where practical, set the appropriate state, and grow it with
scope and checklist sections. Do not alter unrelated manual ideas.

## Finish and synchronize

Before reporting completion:

1. Re-read the active project thread.
2. Re-read the relevant source state in every repository involved.
3. Re-check relevant supplied task materials when they define acceptance
   criteria, constraints, or requested behavior.
4. Check only items supported by completed work or verification.
5. Record the focused tests, builds, manual checks, or other evidence that
   proves the outcome.
6. Set the heading to `DONE`, `EVAL`, or `HOLD` according to its actual state.
7. Add a separate first-level `TODO` for independent residual work.
8. Remove stale statements such as "pending commit" after that event occurs.
9. If the session creates commits or pull requests, record their identifiers
   after success.
10. Do not make commits or pull requests a prerequisite for `DONE`.
11. Leave task working directories and supplied source material intact unless
    the user explicitly asks for cleanup or archival changes.

Do not claim the project record is synchronized until this final pass is done.

## Source and Org boundaries

The Org work tree tracks project state and working material. Source repositories
remain separate.

- Never assume that an Org project directory is a Git repository.
- Never run source-repository Git operations in `~/org/work`.
- Never stage, commit, push, reset, clean, or otherwise manage `~/org/work` as
  part of source repository work.
- Git operations belong to the actual repository roots under `~/src` or another
  explicitly identified source location.
- Do not use repository-local `work/` directories as project or task storage.
- Do not scan repositories for legacy `work/` directories as part of normal
  project discovery or task startup.
- Editing one project file does not grant permission to modify unrelated
  project or client Org files.
- Do not reorganize `~/src` to make it resemble `~/org/work`.
- Do not reorganize `~/org/work` merely to make it resemble `~/src`.

The two trees describe different things:

```text
~/org/work/    logical work, clients, projects, tasks, and working material
~/src/         source repositories using their real Git ownership and names
```

Corresponding names are useful when they naturally occur, but they are a
convention rather than an invariant.

## Restraint

Prefer a small, accurate project record over ceremonial project management.

If substantive work reveals a real follow-up, capture it when it belongs to the
active project and will matter later. Do not manufacture tasks, directories,
client records, project hierarchy, READMEs, or status documents merely to
satisfy the structure.

The filesystem should reflect the work the user actually has, not an idealized
one-to-one relationship between clients, projects, tasks, and repositories.
