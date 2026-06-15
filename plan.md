# Plan

Last updated: 2026-06-15 11:44:27 +02:00

## Current objective

Use the new strategy-structure comparison surface to guide strategy refinement, then keep modularizing the Backtester and Swarm dashboard code.

## Plan map

- Root `plan.md` stays the stable workflow entrypoint for timestamps and the current objective.
- Detailed planning sections now live in companion files under [`plan/`](plan/).
- Use [`plan/current-state.md`](plan/current-state.md) for the rolling implementation snapshot.
- Use [`plan/locked-decisions.md`](plan/locked-decisions.md) for durable project rules and architectural commitments.
- Use [`plan/next-steps.md`](plan/next-steps.md) for the active forward queue.
- Use [`plan/blockers-and-risks.md`](plan/blockers-and-risks.md) for the standing caution list.

## Workflow notes

- `.\workflow_update_plan_progress.ps1` still updates the root `plan.md` timestamp and objective, while prepending summary notes into the companion plan files.
- `progress.md` remains the chronological execution log.
