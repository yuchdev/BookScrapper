# doc-xref

Find and update inbound references to a document path, section heading, anchor, or public symbol.

## Arguments

- `<target>`: a doc path, anchor-bearing path, section name, or public symbol whose references must be updated.

## Workflow

1. Resolve the target precisely.
2. Search Markdown, repo-root docs, `.junie/**/*.md`, docstrings, and code comments for inbound references.
3. Update only the stale references that point to the renamed, moved, removed, or rewritten target.
4. Keep doc text changes minimal: prefer fixing links and anchor text over rewriting unrelated prose.
5. Re-run the relevant documentation checks until the remaining results are either clean or genuinely need human review.

## Use with

- `link-check` for outbound validation.
- `update-docs` when a doc edit created a broader rename-propagation problem.