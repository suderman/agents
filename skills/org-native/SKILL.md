---
name: org-native
description: >
  Writes agent-bound natural-language artifacts directly in valid Org mode.
  Use whenever creating or rewriting a prompt, task, handoff, specification,
  instruction set, runbook, or similar content intended for another AI agent,
  coding agent, harness, or automation system, and whenever the user requests
  Org output. Defaults these artifacts to Org unless the user explicitly asks
  for another format. Does not apply to ordinary conversation, source files,
  or data formats required by a destination system.
license: MIT
---

# Org Native

Write agent-bound documents as Org from the first line. Do not draft Markdown
and convert it afterward.

## Format precedence

Use Org by default for prompts, tasks, handoffs, specifications, instruction
sets, runbooks, and similar natural-language artifacts that the user will give
to another agent or automation system.

An explicit request for Markdown, plain text, JSON, YAML, XML, or another format
wins. A fixed machine-readable schema or source-file format also wins. This
skill does not turn actual configuration, source code, or ordinary answers into
Org merely because an agent will read them.

## Delivery

When returning Org in chat:

- Return one outer code block labeled `org`.
- Put only the Org document inside that block.
- Add no introduction, explanation, or closing text outside the block unless
  the user explicitly asks for commentary.
- The outer fence belongs to the chat response. It is not part of the Org
  document.

When writing directly to an `.org` file, write raw Org without an outer code
fence.

## Document structure

- Use exactly one top-level heading beginning with `* ` in the normal case.
- Put ordinary sections beneath it with `**`, `***`, `****`, and deeper levels
  as needed.
- Do not create sibling `*` headings merely because the document has several
  sections.
- Use multiple top-level headings only when the requested output genuinely
  contains independent documents.
- Do not skip heading levels. A `***` heading must follow content governed by a
  `**` heading.
- Keep heading stars at column zero.

Example:

```org
* Implement request deduplication

** Objective
Prevent the same webhook from being applied twice.

** Requirements
- Store the provider delivery ID.
- Reject a duplicate before applying side effects.

** Verification
1. Send a new delivery.
2. Retry the same delivery ID.
3. Confirm that only one database write occurred.
```

## Lists

- Use `-` for every unordered list item.
- Never use `*` as a bullet, at column zero or at any indentation.
- Use `1.`, `2.`, `3.`, and so on for ordered lists.
- Indent nested list items consistently beneath their parent item.
- Keep continuation text aligned as valid Org list content.

## Literal text

Use `=literal=` for inline code and anything the reader should treat exactly:

- filenames and paths
- commands and command-line options
- keybindings
- variables and environment variables
- function, class, method, and identifier names
- short code fragments and literal values

Do not use Markdown backticks. Keep the surrounding prose outside the Org
literal markers.

## Source blocks

Use native Org source blocks for multiline code, configuration, shell commands,
or machine-readable examples:

```org
#+begin_src python
def greet(name):
    return f"Hello, {name}"
#+end_src
```

- Give every source block an appropriate language when one is known.
- Match every `#+begin_src` with one `#+end_src`.
- Never place Markdown triple-backtick fences inside the Org document.

## Org integrity

- Use Org headings, lists, links, drawers, properties, tables, and blocks with
  valid Org syntax.
- Keep drawers such as `:PROPERTIES:` and `:END:` balanced and directly beneath
  the heading they belong to.
- Keep property names and drawer boundaries at the correct indentation.
- Do not mix Markdown headings, bullets, inline-code syntax, or fenced code
  blocks into the Org document.
- Preserve valid Org syntax when rewriting existing Org. Do not flatten or
  unnecessarily reorganize the user's structure.

## Final check

Before sending or writing the document, inspect the finished Org itself, not a
Markdown draft.

1. Count lines matching a single top-level heading, `^\* `. There should be
   exactly one unless the request truly contains independent documents.
2. Confirm every other heading starts with at least `** ` and heading depth does
   not jump.
3. Confirm no unordered list item uses `*`, including indented items.
4. Confirm unordered items use `-` and ordered items use `1.`, `2.`, `3.`, and
   so on.
5. Confirm literals use `=...=` rather than backticks.
6. Confirm multiline code uses balanced `#+begin_src LANGUAGE` and
   `#+end_src` lines.
7. Confirm no Markdown heading or triple-backtick fence appears inside the Org
   document.
8. Confirm drawers, properties, indentation, and nested structures remain valid
   Org.
9. When returning chat output, confirm nothing appears outside the outer Org
   code block unless commentary was requested.

If any check fails, fix the Org before returning it.
