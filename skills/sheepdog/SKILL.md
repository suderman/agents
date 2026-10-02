---
name: sheepdog
description: >
  Let Hermes supervise and babysit an explicitly assigned Pi agent through Herdr.
  Use when asked to babysit ongoing work, review timed check-ins, correct direction,
  or advance approved slices. Requires a project mandate and a bounded watch.
compatibility: Hermes supervisor, interactive Pi worker, Herdr, Python 3 on Linux.
---

Read `sheepdog.org` completely before starting or handling a review. Resolve its
script paths relative to this skill directory. This capability is opt-in, not a
global permission to control agents or publish projects. Fresh runs default to a
900-second soft ACK warning and a separate 1800-second hard timeout, capped by
watch expiry. `--review-seconds` sets the soft threshold;
`--review-hard-seconds` sets the hard timeout. Legacy bindings retain their
original hard deadline and must not be migrated or revived.
