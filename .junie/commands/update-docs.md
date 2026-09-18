# update-docs

Maintain documentation integrity after file moves, heading changes, or API/doc behavior changes.

## Modes

- No argument: scan mode for the documentation corpus.
- `<path>`: path mode for a specific edited document.

## Scan mode

1. Audit Markdown references across `docs/`, repo-root Markdown, and `.junie/**/*.md`.
2. Find missing-file references and broken anchors.
3. Auto-fix only high-confidence target updates.
4. Write out the remaining ambiguous items as a review report the user can act on.
5. Re-run until the corpus is clean or only human-decision items remain.

## Path mode

1. Resolve the edited target document.
2. Detect removed or renamed headings and any resulting stale inbound references.
3. Update Markdown, docstrings, and comments that still point at the old headings or paths.
4. Validate the target's outbound links and then the broader doc corpus.
5. Continue until stale references are gone or the remaining cases genuinely need human judgment.

## Use with

- `doc-xref` for inbound reference rewrites.
- `link-check` for outbound validation.

## Junie notes

- Junie has no automatic rescheduling loop here; rerun manually until the documentation state converges.