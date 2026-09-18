# test-gap

Identify the highest-value missing tests for a module, package, or change scope.

## Arguments

- `[path]`: optional scope to inspect; default to the changed or requested area.

## Workflow

1. Establish current coverage or missing-behavior evidence for the scope.
2. Map uncovered lines and branches back to behaviors, failure modes, and user-visible risk.
3. Rank gaps by blast radius, not by line count alone.
4. For the highest-priority gaps, suggest concrete tests, not vague advice.
5. If the task is to close those gaps immediately, hand off to `testing-expert`.

## Output

- Prioritized findings such as P0/P1/P2, each tied to a specific behavior and recommended test.