---
name: sheepdog
description: >
  Let a Pi supervisor babysit an explicitly assigned Pi worker through Herdr.
  Use when asked to babysit ongoing work, review timed check-ins, correct direction,
  or advance approved slices. Requires a project mandate and a bounded watch.
compatibility: Separate interactive Pi supervisor and worker sessions, Herdr, Python 3 on Linux.
---

Read `sheepdog.org` completely before starting or handling a review. Resolve its
script paths relative to this skill directory. This capability is opt-in, not a
global permission to control agents or publish projects. Fresh runs default to a
900-second soft ACK warning and a separate 1800-second hard timeout, capped by
watch expiry. `--review-seconds` sets the soft threshold;
`--review-hard-seconds` sets the hard timeout. Legacy bindings retain their
original hard deadline and must not be migrated or revived. New and active
bindings require two distinct Pi sessions; old Hermes bindings cannot continue.
