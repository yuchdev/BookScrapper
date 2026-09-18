# document-tests

Standardize test docstrings and classify existing tests without changing their logic.

## Arguments

- `[path]`: optional test scope; default to the repository's test tree.

## Workflow

1. Inspect the target tests and classify each as unit, mocked integration, real integration, or end-to-end.
2. Add or normalize docstrings using the repo's preferred test-documentation style.
3. If classification is ambiguous, stop guessing and inspect the test body or route the work to `test-documenter`.
4. Verify that collection still succeeds and that only documentation text changed.

## Rules

- Do not alter test logic, fixtures, or assertions as part of this command.
- Keep any classification rationale short and explicit.