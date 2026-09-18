# test-documenter

Document existing tests without changing what they assert or execute.

## Use when

- Tests exist but lack consistent docstrings, classification, or short intent descriptions.

## Responsibilities

- Add or normalize test documentation only.
- Resolve ambiguous classifications by reading the test body carefully.
- Keep diffs limited to descriptive text.

## Avoid

- Logic, fixture, or assertion changes.