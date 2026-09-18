# link-check

Validate outbound documentation links and heading anchors.

## Arguments

- `[path ...]`: optional file or directory scope. With no arguments, check the full documentation corpus.

## Workflow

1. Check Markdown links in the requested scope.
2. Verify that relative targets exist and that anchor fragments resolve to real headings or explicit anchors.
3. Fix broken targets or stale anchors with the smallest safe edit.
4. If a rename or move caused the breakage, follow up with `doc-xref` so inbound references are updated too.
5. Re-run until the scope is clean or the remaining issues clearly need human review.

## Corpus

- Include `docs/`, repo-root Markdown, and `.junie/**/*.md` when they exist.