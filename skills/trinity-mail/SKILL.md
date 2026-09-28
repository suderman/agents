---
name: trinity-mail
description: Keep ~/org/life/trinity.org current from local pallisersd.ab.ca school emails. Use when asked to check Trinity Christian School mail, ingest school updates, or update Nathan's Grade 3B and Davy's Grade 5D notes from email.
compatibility: Requires notmuch; PDF inspection may require pdftotext via nix shell.
---

# Trinity mail updates

Use this with the `notmuch-org-mail` skill. Read that skill before searching mail; its safety, MIME, attachment, and verification rules apply here. This skill adds the Trinity-specific selection and editing rules. Do not convert messages into separate Org archives for a routine update.

## Find what is new

1. Read `~/org/life/trinity.org`, especially the latest weekly bulletin attachment and dated class notes. Use the most recent already-covered school message or bulletin as a starting point, searching at least seven days before it. This overlap catches corrections, delayed mail, and messages omitted from an earlier pass. If there is no reliable starting point, search the last 30 days and expand when needed. State the inclusive range used.
2. Check the local notmuch setup as directed by `notmuch-org-mail`. Search `from:pallisersd.ab.ca and date:YYYY-MM-DD..` with `notmuch search --format=json --output=summary --sort=newest-first`; obtain exact message IDs with `--output=messages`. Do not rely on `tag:unread`: an unread message may be a duplicate, and a read one may contain new facts. Search summaries first, then read plausible school, office, Grade 3B, Grade 5D, or subject-teacher messages with `notmuch show --format=text --entire-thread=false -- 'id:...'`. Leave unrelated district mail alone. Do not read whole threads by default.
3. Compare each message with existing notes before editing. Two emails with the same subject may have identical attachments; a filename may name the wrong week. Check attachment content and hashes rather than assuming either the subject or filename is correct.

## Update Trinity notes

- Keep the existing top-level heading and its Org ID. Put class tasks under `Grade 3B` or `Grade 5D`, dated school-wide items under `2026-27 school events`, lasting policies under `School notes`, and useful PDFs under `Attachments`. Match current structure if the school year or classes change.
- Prioritize upcoming deadlines, schedule changes, classwork, teacher requests, useful links, and school rules. Correct stale recurring advice when newer mail supersedes it. Do not restate old reminders already covered.
- Do not add optional events, contradictions, or requests to confirm a typo merely because they appeared in a bulletin. Include uncertainty only when it affects an action the family might take. Never turn a contradictory weekday/date into a confirmed Org timestamp; if relevant, explain the conflict instead.
- Preserve exact dates, weekdays, times, page numbers, and URLs from the source. Verify weekdays independently. Use Org active timestamps for events and due dates. Distinguish a linked worksheet from an online submission form; a Drive copy is not necessarily a form to submit.
- For attachments, derive the Org ID attachment directory from the existing heading as described in `notmuch-org-mail`. Extract to a temporary file, inspect type and content, hash it, then copy only a useful nonduplicate. Never overwrite an existing file. If the sender's safe filename describes the wrong week, use a content-accurate filename and mention the discrepancy in the report. Link with `[[attachment:filename.pdf][description]]`. An emailed flyer need not be saved if its useful details are already in the notes or an attached bulletin.
- Re-read `trinity.org` immediately before editing. Keep changes compact. Do not add a separate processing log or an archive of every email.

## Verify and report

Re-read the changed section. Check all added attachment links against the Org ID directory, types and hashes against the extracted source, and new dates and facts against their messages. Re-run the focused notmuch search for mail that arrived during review. Remove temporary files. Report the inclusive range, number of messages reviewed, changes made, attachments saved, and any relevant unresolved ambiguity. Do not change mail tags, send replies, or mark mail read unless asked.
