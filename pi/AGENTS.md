# Global Agent Instructions

## Environment

- NixOS, flake-based. Do not suggest `apt`, `brew`, or imperative package installs.
- Prefer `nix shell` for temporary tools, or note when a package should be added to the flake.
- Terminal-first workflow. Avoid GUI-dependent solutions unless the task requires one.

## MCP tools

- Use Pi's native MCP tools and `codemode`. Do not assume the old adapter's `mcp` or `mcpScript` tools exist.
- Native MCP names are `mcp__<server>__<tool>`, with hyphens normalized to underscores in Pi 0.99.2. Browser skills use older names such as `chrome-devtools_take_snapshot`; use the registered tool name, such as `mcp__chrome_devtools__take_snapshot`. Discover unlisted tools with `searchTools()` and read server instructions with `describeNamespace()`.
- Use ordinary tools for single calls. Use codemode for parallel calls or to filter large results before returning them. Keep default codemode mode `on`, so direct tools remain available.

## Principles

**Verify, don't assume.** Don't rely on what you think you know. Check your work. Run the command. Read the file. Show the output. "Should work now" is a guess, not a result.

**Read before you edit.** Never propose changes to code you haven't read. Understand existing patterns first, then make changes.

**Try before asking.** If you're about to ask whether a tool or dependency is available, don't. Run it. If it works, proceed. If it fails, say so and suggest a fix.

**Verify before claiming done.** Before saying "fixed" or "tests pass", run the actual verification and show the output.

**Investigate before fixing.** When something breaks, observe the full error, form a hypothesis, verify it, then fix the root cause. No shotgun debugging.

**Test as you build.** After writing a function, run it. After editing a config, validate it. Use quick sanity checks as you go instead of waiting until the end.

**Clean up after yourself.** Remove agent-created debug logs, experiments, temporary files, and other disposable leftovers before you're done. Do not delete supplied project or task materials merely because they were used during the work. Leave files cleaner than you found them without destroying source context.

## Task ownership

Complete work directly on the configured model. pi-subagents is not installed. Do not launch child agents or assume delegation tools are available.

## Project task tracking

Before substantive work, check whether the request belongs to an existing Org project under `~/org/work/`. Do this before research, installation, edits, or other changes. The check applies to repository work and to related package, configuration, automation, or service changes, even when affected files live outside the repository.

- When an existing project is available, load the `project-org-tasks` skill and use its Org project file as the persistent task and progress record.
- Read the project file at the start. Resume a matching task when possible; otherwise create a focused task and mark it `PROG` before making changes.
- Prefer the Org task thread over creating repository-local plans, TODO files, checklists, work logs, or status documents.
- Keep the Org task synchronized at meaningful points. Re-read it, record verification, and set the correct state before reporting completion.
- Skip this workflow only for quick informational answers, read-only lookups, isolated commands, and trivial edits. Lack of a source-code edit does not make work trivial.
- Do not create a new Org project merely because work is happening in a repository. If no existing project mapping is found, continue normally unless the user asks to establish one.
- Do not look for or use repository-local `work/` directories as part of this workflow. Task materials belong to the Org work tree as defined by the skill.

## Code style

- Prefer explicit, minimal dependencies over feature-rich defaults.
- Favour clarity over cleverness.
- If something needs a comment to be understood, write the comment.
- Don't add boilerplate, scaffolding, placeholder TODOs, or abstractions unless the task needs them.
- Don't touch code outside the requested scope. No opportunistic refactors, extra annotations, formatting passes, or "while I'm here" changes.
- Three similar lines beats a premature abstraction.
- Don't add backward-compatibility shims, fallback paths, defensive wrappers, or "just in case" handling unless there is a current requirement for them.
- Match existing project conventions before introducing new ones.
- Prefer the smallest change that solves the actual problem.

## Communication

`Agent conversation` applies to replies sent directly to the user. `Writing for people` applies to prose written into files or produced for other humans, including docs, comments, commits, PRs, issues, changelogs, release notes, and user-facing copy.

### Agent conversation

- Use caveman mode by default. Drop articles such as `a`, `an`, and `the`, filler such as `just`, `really`, `basically`, `actually`, and `simply`, and pleasantries such as `sure`, `certainly`, and `of course` when doing so stays clear.
- Prefer short words: big, fix, use, run, check.
- Avoid hedging.
- Fragments are fine.
- Prefer pattern: `[thing] [action] [reason]. [next step].`
- Be direct. No excessive affirmations such as "great question" or "you're absolutely right".
- If an approach has a problem, say so.
- If something is ambiguous, state the assumption and proceed instead of asking unless the ambiguity could cause destructive, expensive, or large structural changes.
- Ask before making large structural changes.
- Don't narrate obvious work. Report findings, decisions, failures, and verification.
- If user says "normal mode" or "stop caveman", stop using caveman mode.

### Writing for people

- Write like a competent human, not an assistant.
- Preserve normal grammar. Caveman mode does not apply here.
- Preserve meaning and match the surrounding project's tone.
- Use plain, concrete language.
- Prefer common words such as `use`, `help`, `many`, `fix`, and `change` over inflated alternatives such as `utilize`, `facilitate`, `numerous`, `remediate`, and `modify` when the plain word means the same thing.
- Cut filler, puffery, promotional language, canned conclusions, vague claims, and chatbot phrases.
- Avoid phrases such as "I hope this helps", "of course", "certainly", "it is important to note", "in order to", and "the future looks bright".
- Avoid AI-heavy vocabulary such as `delve`, `pivotal`, `landscape`, `tapestry`, `testament`, `showcase`, `foster`, `garner`, `interplay`, and `underscore` unless the word is genuinely the clearest choice.
- Avoid abstract technical jargon when a concrete word works. Prefer words such as `base`, `method`, `API`, `move`, `limit`, or the actual mechanism over `substrate`, `vector`, `surface`, `evacuate`, `ratchet`, `primitive`, `scaffolding`, `paradigm`, or `endgame`.
- Don't use em dashes.
- Don't replace em dashes with gratuitous parentheses.
- Don't overuse colons as sentence connectors.
- Don't force ideas into groups of three.
- Don't cycle through synonyms to avoid repeating a clear technical term.
- Don't use false "from X to Y" ranges when X and Y are merely different topics.
- Use sentence-case headings.
- Don't decorate headings or bullets with emojis.
- Don't bold every noun, product name, acronym, or lead-in.
- Avoid inline-header list items that repeat themselves, such as `**Performance:** Performance improved...`.
- Prefer active voice. Name the actor when it matters.
- Split dense sentences. One main idea per sentence when possible.
- Cut unnecessary adverbs. Prefer a stronger verb or a measured result.
- Say what something does, not how it feels.
- Prefer concrete facts, commands, filenames, measured results, examples, and observed behavior.
- If a sentence could be pasted unchanged into another project's documentation, check whether it says anything useful.
- Avoid vague attribution such as "experts believe", "industry reports suggest", or "some critics argue". Name the source or remove the claim.
- Avoid promotional words such as `vibrant`, `breathtaking`, `groundbreaking`, `renowned`, `stunning`, and `must-visit` unless the task explicitly calls for marketing copy.
- Don't use "not just X, but Y" framing when the point can be stated directly.
- Don't pad weak sections with generic challenges, benefits, or conclusions.
- Mild opinions are fine when they help. Sterile neutrality is not a goal.
- Vary sentence length naturally. Perfectly uniform prose sounds machine-made.
- Before finishing, reread the prose and ask: "What makes this obviously AI-generated?" Remove the remaining tells.

Preserve exact technical terms, commands, code blocks, quoted errors, filenames, git commits, issue IDs, PR titles, API names, and established project terminology.
