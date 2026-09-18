# pr-review

Run a combined correctness and security review over a PR, branch diff, or working-tree diff.

## Arguments

- `[review target]`: optional PR number, branch, or diff target. If omitted, review the current working tree.

## Workflow

1. Resolve the review scope.
2. Run `feature-reviewer` and `security-auditor` in parallel when possible.
3. Merge their findings into a single verdict with required fixes, optional follow-ups, and any blockers.
4. If security returns a critical blocker, the overall result must not approve the change.
5. If reviewers lack enough evidence, return that limitation explicitly instead of over-approving.

## Output

- A single review summary with verdict, key findings, and next actions.