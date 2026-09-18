# adr-write

Scaffold a new ADR in `docs/adr/` for a named design decision.

## Arguments

- `<title>`: the ADR title.

## Workflow

1. Determine the next zero-padded ADR number from `docs/adr/`.
2. Read the canonical ADR template used by this repo and preserve its heading structure exactly.
3. Seed the context from recent repo history and any relevant open issues or roadmap items.
4. Create `docs/adr/NNNN-<kebab-title>.md` with status `Proposed`.
5. Include the chosen option and at least one rejected alternative with a reason.
6. Add or update the ADR index entry in `docs/README.md`.
7. Verify cross-references before finishing.

## Output

- Print the created ADR path and a one-line summary.

## Notes

- This command scaffolds and seeds the ADR. Use `app-architect` when the decision content itself needs deeper design work.