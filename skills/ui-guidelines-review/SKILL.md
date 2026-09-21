---
name: ui-guidelines-review
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# UI Guidelines Review

Review UI implementations for compliance with Web Interface Guidelines.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Scope

Use this skill for guideline-based UI reviews of code or markup.

- If the task is primarily a live-browser inspection or reproduction task, also
  load `browser-testing`.
- If the task requires temporary CSS or JavaScript experiments in the browser,
  also load `web-inspector-editing`.

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use `webfetch` to retrieve the latest rules. The fetched content contains all the
rules and output format instructions.

## Usage

When a user provides a file or pattern argument:

1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files are specified, ask the user which files or file patterns to review.

If the user provides only a live URL, inspect the rendered page first and ask
whether they also want file-mapped findings.
