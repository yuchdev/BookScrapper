# verify-subtask

Compare an implementation against a roadmap or subtask spec and return a compliance verdict.

## Arguments

- `<path>`: path to the authoritative task or subtask spec.

## Workflow

1. Resolve the spec file and the implementation scope it governs.
2. Compare the current code and tests against the spec's required files, symbols, behaviors, and constraints.
3. Record a compact compliance matrix.
4. Return one of `PASS`, `PARTIAL`, or `FAIL` with the blocking or notable gaps.
5. If the verdict is not `PASS`, recommend the smallest safe next action.

## Use with

- `subtask-verifier` for the detailed comparison.
- `pr-review` and `test-gap` once core compliance is established.