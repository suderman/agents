---
name: nf-wordpress
description: >
  Develop and maintain WordPress projects using nonfiction's nf tooling and
  conventions. Use when a project contains nf.json, uses the nf CLI, or involves
  WordPress theme development, local environments, packaging, deployment, or
  synchronization. For greenfield sites, follow nonfiction/themestarter and
  nonfiction/theme patterns including Timber/Twig, Composer, Vite, and
  colocated feature modules. For inherited sites, inspect and preserve the
  existing theme architecture and framework conventions rather than forcing
  the nonfiction starter structure.
---

# nf WordPress

Use this skill for current nf-based WordPress work. It describes the durable
operating model, not a platform-to-nf migration procedure or a frozen command
reference.

## Sources of Truth

When evidence conflicts, use this order:

1. The active repository, runtime behavior, `AGENTS.md`, and project docs.
2. The installed `nf` CLI help and the current nf source and docs.
3. Current `nonfiction/themestarter` and `nonfiction/theme` source.
4. Completed nf projects with the same architecture.
5. Historical migration skills and old project documentation.

Use `nf help` and `nf <group> help` for exact current commands and flags. Do not
guess from memory or copy an old invocation merely because it appears in a
migration ledger.

Use <https://nonfiction.github.io/nf/> and the current `nonfiction/nf`,
`nonfiction/themestarter`, and `nonfiction/theme` repositories when local source
is unavailable.

## Start With Evidence

Before proposing architecture or editing files:

1. Read `AGENTS.md`, `README.md`, `nf.json`, and nearby documentation.
2. Inspect repository status and do not overwrite unrelated changes.
3. Inspect configured paths and actual Composer, npm, Vite, PHP, Twig, and
   WordPress wiring rather than assuming `theme/` or a starter architecture.
4. Check `nf theme tasks` against real files and inspect similar modules.
5. Identify persisted contracts, then choose the smallest fitting change.

An `nf.json` file identifies an nf project. It does not prove that the site uses
Timber, Vite, Composer, the shared theme package, or a repository-owned theme.

## Classify the Project

Choose one path before changing structure:

### Greenfield Starter

Use the current `nonfiction/themestarter` as a copy-and-trim baseline. Follow
its current nf manifest, `theme/` deploy unit, Timber/Twig rendering, Composer
dependencies, Vite asset graph, and colocated feature modules. Delete examples
and optional tooling the site does not need.

### Existing Starter Consumer

Preserve the established `Nonfiction\Theme\App` bootstrap, application imports,
Twig paths, manifest conventions, and module layout. Extend nearby patterns
instead of re-scaffolding the theme.

### Inherited Site

Preserve its proven architecture whether it is a classic PHP theme, child
theme, vendor theme, page-builder site, bespoke Timber theme, or another
framework. Do not add Timber, Vite, Composer, `nonfiction/theme`, or starter
directories solely to make it resemble a greenfield project.

### No Repository Theme

This is valid. nf can bootstrap public, cached, or externally sourced themes
without owning theme source. Work in configuration, plugins, or persisted site
state as appropriate; do not create a repository theme without a demonstrated
need.

### Shared Package Work

Keep `nonfiction/theme` reusable; site-specific behavior belongs in consumers.

## nf Project Model

nf is an internal CLI for WordPress project and environment operations. It is
not a WordPress application framework.

The global hierarchy is:

```text
provider -> target -> site -> environment
```

Repository context comes from `nf.json`, which must be beside the repository's
`.git` directory. Current manifests use version `2` and are strict: unknown
fields and invalid combinations are errors.

The project manifest contains:

- `version`: exactly `2`.
- `project`: the project `slug` and required `password_version`.
- `wordpress`: ordered themes plus optional plugins, defines, and aliases.
- `local`: optional local-environment overrides only.
- `remotes`: optional project aliases for remote environments.

Do not copy obsolete fields from an old README or migration skill. Validate the
manifest with the current CLI after editing it.

## Themes

Treat `wordpress.themes` as an ordered environment-bootstrap checklist:

- At least one theme is required.
- The first theme is the intended active theme.
- A project may contain at most one repository-sourced theme.
- The conventional repository theme uses the project slug and path `theme`, but
  inherited projects may differ or have no repository theme.
- Parent/child ordering and slugs are persisted behavior; preserve them.
- Theme entries may come from wordpress.org, the repository, cache, URL, path,
  or an environment-variable-backed source supported by the current CLI.
- Theme package settings and project tasks belong to the repository theme.

Use nf theme status/diff/install/pull/adopt operations according to current
help. Recovery or adoption operations can modify source and may require a clean
worktree; inspect their behavior before running them.

## Plugins

Treat `wordpress.plugins` as an environment-bootstrap checklist, not a complete
lifecycle manager or a record of every historically installed plugin.

- Public plugin strings use wordpress.org defaults.
- Object entries can control source, installation, activation, auto-updates,
  and explanatory notes.
- Repository plugins conventionally live under `plugins/<slug>`.
- Repository plugins are bind-mounted locally and packaged for remote upload.
- Private or licensed plugins normally use the nf cache; never commit licenses,
  credentials, or downloaded private artifacts merely for convenience.
- Cache misses should fail visibly. Do not invent a fallback source.
- Use `install: false` only to document a real manual prerequisite.
- Select plugins from current code and runtime evidence, not stale Composer
  requirements or migration inventories.

Put durable site business behavior in a project plugin when it should survive
theme changes. Keep presentation and template behavior in the theme. Preserve
third-party plugin ownership where replacing it would create unnecessary
maintenance or break persisted state.

## Defines and Secrets

Project defines are declared in `nf.json` and reconciled into nf's managed
WordPress configuration block.

- Commit safe literal values directly when appropriate.
- Store secret values through the current encrypted define workflow.
- Commit `nf.age` when it contains the project's encrypted references.
- Never put plaintext secrets in `nf.json`, shell history, logs, docs, or Git.
- The encryption identity depends on the configured password salt; inspect
  current rekey guidance before changing salts.
- Use selector-specific values when environments legitimately differ.
- Do not hand-edit nf's managed define block or create duplicate manual defines.
- Treat commands that reveal define values as sensitive output.

Defines do not move with normal environment data synchronization. Reconcile
them separately and deliberately.

## Aliases

Aliases expose selected `wp-content` paths at project-root names. nf manages
the corresponding root symlinks without replacing real files or directories.

- Keep alias targets inside `wp-content` or its descendants.
- Use aliases only for paths the project genuinely owns or needs to expose.
- Do not replace an alias with copied runtime data.
- Let nf reconcile managed symlinks instead of scripting competing links.

## Tasks

Repository-theme tasks run from the project root. A task may be a shell string,
an argument array, or an object with a description and command.

- Keep task names and behavior consistent with files that actually exist.
- Prefer a small set of useful `composer`, `npm`, `build`, `watch`, and `check`
  tasks over wrapper layers.
- Preserve argument passthrough after `--` when invoking task-backed commands.
- Do not retain stale tasks for dependency managers or build tools the project
  no longer has.
- Run theme commands through nf when project docs establish that workflow.

## Local Environments

`nf env up` creates or reconciles the managed local WordPress environment. It is
intended to be idempotent and configures the project themes, plugins, defines,
Mailpit, and debugging behavior.

- Keep `local` configuration limited to genuine overrides.
- Generated environments, caches, and CLI state live outside the repository.
- The default uploads integration uses a managed project-root symlink; do not
  replace it with a committed upload tree.
- Use `nf env show`, WordPress CLI passthrough, logs, and Mailpit to inspect the
  real runtime.
- `nf env reset` is destructive to local state even though nf creates a safety
  snapshot. Confirm intent and inspect current help first.
- Snapshot before risky local imports or broad data changes.
- Never treat a successful container start as proof that the site works.

## Packaging

`nf theme package` stages the configured repository theme and creates a release
archive.

- It installs production Composer dependencies in staging without replacing the
  working theme's `vendor` directory.
- It excludes development-only files according to current packaging rules.
- It does not run npm or build frontend assets.
- Required compiled output must exist before packaging.
- Run the project's checks and build first, then inspect the dry run and actual
  archive when release integrity matters.
- Confirm the archive has one correctly named theme root, production autoloading,
  built assets, and no secrets or local state.

Do not repeat historical claims about package contents without inspecting the
current CLI and resulting archive.

## Deployment and Rollback

Theme deployment is a packaged release operation:

- nf installs configured non-repository theme dependencies first.
- It uploads and extracts a release, updates the active theme, records release
  metadata, and retains a bounded release history.
- Provider-specific restart and cache behavior is controlled by current nf
  options and integrations.
- Rollback switches to a prior recorded release without rebuilding or uploading
  a new package.

A theme deployment does not transfer the database, uploads, define values, or
all WordPress settings. State migration and code deployment are separate
operations.

Before deploying, confirm the remote and resolved target, worktree, and release
contents. Build, check, package, and inspect as appropriate; obtain explicit
approval for production effects. Verify the deployed runtime, retain rollback,
and record the release identifier when relevant.

## Data Synchronization

Environment push/pull operations can move database state and selected runtime
artifacts such as uploads, plugins, and languages. They intentionally do not
replace the theme release or synchronize defines.

- Treat production data operations as high risk.
- Inspect the source, destination, table prefix, selected artifacts, and dry run.
- Require explicit confirmation before destructive or production-affecting
  synchronization.
- Preserve target-owned mu-plugins and environment-specific configuration.
- Do not assume theme deployment carries template assignments, settings,
  widgets, content, or uploaded media.
- Use a full site export for a deliberate handoff when that is the actual goal.

## Greenfield Theme Conventions

For a new site, start from the current themestarter rather than reconstructing
its layout from this document.

Copy the current starter, rename project identity carefully, and remove sample
features the project does not need. Its normal shape is a root `nf.json`, a
`theme/` containing bootstrap, dependency, build, `app/`, `config/`, and optional
`src/` files, plus optional root `plugins/`.

### Bootstrap and Rendering

- Require Composer autoloading from the consuming theme.
- Bootstrap shared infrastructure through `Nonfiction\Theme\App` using the
  current package API.
- Use Timber v2 and Twig for rendering.
- Keep PHP responsible for registration, data preparation, permissions, and
  WordPress hooks.
- Keep Twig responsible for presentation with explicit context.
- Register global Twig views and module-local views through the established app
  bootstrap.
- Keep business logic out of Twig and shared package code.

### Colocated Features

Keep files together when they implement one feature. A block directory may
contain `block.json`, registration PHP, Twig, editor and frontend JavaScript,
CSS, and small assets.

Generic blocks belong under `app/blocks`. Post-type- or feature-specific blocks
belong under that feature's module. Colocate PHP registration, Twig views,
editor code, frontend behavior, styles, metadata, and small assets when they
change together.

Use `app/views` for global layouts and shared partials. Use `theme/src` only for
project-local reusable PHP infrastructure; do not duplicate classes already
provided by `nonfiction/theme`.

### Assets

- Preserve the starter's current Vite manifest contract and entry groups.
- Typical concerns include head, body, blocks, editor, and admin assets.
- Keep frontend, editor, and admin responsibilities separate.
- Import module assets through the established graph instead of adding ad hoc
  enqueue paths.
- Verify emitted manifest paths and browser requests after changing Vite config.
- Do not apply a universal Vite `base` value copied from an old migration skill.
- Commit built output only when the project and packaging workflow require it.

### Shared Theme Package

Consume `nonfiction/theme` through Composer/Packagist in normal projects. Use a
Composer path repository only while deliberately developing the package and a
consumer together.

The package provides reusable bootstrap, helpers, asset/manifest support,
Timber adapters, and WordPress registrars.

It does not own client templates, content models, design, routes, menus, blocks,
or integrations. Do not add compatibility shims for removed legacy package APIs
without a concrete persisted or external consumer.

## Inherited Site Rules

For inherited projects, inspect before normalizing:

- Preserve active and parent theme slugs, template filenames, and hierarchy.
- Preserve the existing PHP bootstrap, framework, namespace, and view resolver.
- Preserve the existing asset pipeline and committed-output policy.
- Preserve child-theme boundaries and vendor-theme update paths.
- Preserve builder-managed content and plugin state unless replacement is the
  explicit project goal.
- Verify manifest tasks against the filesystem; stale tasks are not evidence of
  a missing build system.
- Do not move files into starter directories just for consistency.
- Add a dependency only when the existing architecture or requested feature
  requires it.
- Modernize locally and incrementally rather than rewriting a stable theme.

An inherited Timber theme can remain in its own `inc`, `blocks`, and `views`
layout. A classic PHP theme can remain classic. A child theme can remain a
minimal child theme. nf supports each of these.

## Persisted WordPress Contracts

Treat block names and markup, shortcodes, post types, taxonomies, rewrites,
template filenames, theme slugs, menu locations, widget IDs, options, custom
fields, routes, AJAX actions, cron hooks, capabilities, URLs, attachment data,
custom elements, forms, plugin tables, and integration identifiers as public
APIs whenever content or production state may depend on them.

Search code and, when authorized, runtime/database evidence before renaming or
removing a contract. Prefer a compatibility-preserving implementation over a
content rewrite. If a migration is unavoidable, make it explicit, reviewable,
replayable, and separately approved.

## Security and Operational Safety

- Never invent remotes, provider targets, plugin URLs, credentials, or licenses.
- Never expose secrets through define inspection, shell arguments, logs, or
  generated documentation.
- Escape output, sanitize and validate input, verify nonces, and check
  capabilities in WordPress code.
- Treat database imports, pushes, resets, plugin adoption, and remote operations
  according to their real blast radius.
- Use dry runs where supported, but do not mistake a dry run for runtime proof.
- Do not deploy, synchronize production data, or mutate production without the
  user's explicit approval.
- Keep ignored SQL, uploads, plugin snapshots, and other reference artifacts
  immutable unless the task specifically requires changing them.
- Do not claim parity, performance, compatibility, or security without testing
  the relevant path.

## Verification

Use the narrowest checks that prove the requested behavior, then expand as risk
requires:

- Configuration: validate `nf.json`; inspect relevant themes, plugins, aliases,
  defines, remotes, tasks, paths, and sources without revealing secrets.
- PHP/Twig: run established checks; exercise the route, admin action, block, or
  template; inspect PHP/debug logs.
- CSS/JavaScript: run checks and builds; inspect manifests, browser requests,
  console output, and relevant frontend, editor, admin, and responsive paths.
- Packages/releases: inspect dry-run and archive contents, production autoloading,
  compiled assets, resolved remote, deployed behavior, and rollback data.
- Data: record endpoints, snapshot as appropriate, inspect the dry run and table
  prefix, then verify content, URLs, media, plugin state, and logs.

Always review the final diff and repository status. Report checks actually run,
remaining risks, and anything that could not be verified.
