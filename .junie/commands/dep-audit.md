# dep-audit

Run a dependency audit for vulnerabilities, risky version drift, and license concerns.

## Workflow

1. Inspect the active dependency manifests.
2. Run the best available vulnerability tooling for the current environment.
3. Review direct dependencies for outdated versions that carry plausible security impact.
4. Classify dependency licenses into allow, flag, or block based on the repo's intended distribution model.
5. Summarize findings with package, current version, risk, remediation path, and any follow-up validation needed.
6. For deeper or scheduled reviews, delegate the durable report write-up to `background-reviewer`.

## Rules

- Treat HIGH and CRITICAL findings as urgent.
- If tooling is unavailable, say so explicitly instead of pretending the audit is clean.
- When manifests changed, pair this with focused regression tests for the affected dependency surface.