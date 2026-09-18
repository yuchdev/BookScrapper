# implement-milestone

Drive an entire roadmap milestone to completion while preserving task order, shared contracts, and milestone-level gates.

## Arguments

- `<milestone>`: a milestone number, slug, or title that resolves unambiguously.

## Workflow

1. Resolve the milestone folder and read its plan and status state.
2. On a cold start, digest the milestone once: task list, dependency order, shared contracts, task-level risk markers, and milestone exit gates.
3. Reconcile planned work against the as-built code before implementing anything. If the code already diverged materially from the plan, stop and get a ruling before continuing.
4. Audit decomposition: each planned task should have a task folder, README, and subtask specs. Missing decomposition may be authored through `app-architect`; genuinely new scope requires user confirmation.
5. Execute one subtask at a time through the `implement-subtasks` workflow, while updating milestone status after each completed subtask.
6. When a task closes, append a concise delivered-and-tested summary to `status.md` and mark the task complete.
7. When all tasks are done or explicitly deferred, run the milestone exit gates and documentation checks, then finish with a closing summary.

## Junie notes

- Junie does not expose Claude's self-rescheduling wakeup loop. Resume manually when needed.
- Do not invent hidden milestone cursor files under `.junie/`; keep the durable record in roadmap docs and brief session summaries.