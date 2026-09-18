# implement-subtasks

Drive one roadmap task to completion one subtask at a time.

## Arguments

- `<task>`: a task number, milestone/task pair, or task title that resolves unambiguously.

## Workflow

1. Resolve the milestone, task row in `status.md`, task folder, task `README.md`, and subtask queue.
2. If the task is already complete, verify it instead of rebuilding it.
3. Choose exactly one active subtask per pass: first partial, otherwise first not-started.
4. Read only the chosen subtask spec in full.
5. Delegate implementation to the right specialists: `python-expert`, `testing-expert`, `scraping-expert`, `docs-writer`, `docs-updater`, or `security-auditor` as needed.
6. Stop and ask the user when the spec is ambiguous or a contract-level design fork appears.
7. Run the narrowest meaningful verification for that subtask, then run `verify-subtask`.
8. Conditionally run the other gate workflows that actually apply: `test-gap`, `dep-audit`, `link-check`, `pr-review`, and the `secret-scan` skill.
9. Update only the affected row in the task `README.md`; when the overall task is truly complete, update `status.md`, run broader closing validation, and stop.

## Junie notes

- Junie has no automatic wakeup loop here. Stay in one session when practical; otherwise reinvoke this command manually with the same task and resume from the authoritative docs.
- Keep progress in the repo's own status files, not hidden loop-state files.