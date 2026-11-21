# 0003 — Force charge only on SMART dispatches

- **Date:** 2026-11-21
- **Status:** Accepted
- **Deciders:** Owner (21-11-26, confirmed twice), Claude session

## Context
ADR 0002 starts a force charge for any dispatch outside 23:30-05:30. A boost or
bump dispatch can bill at the expensive rate. The battery must not charge then.
Card: IOG-24. Follows IOG-23.

## Decision
This supersedes the trigger rule of ADR 0002. The rest of ADR 0002 stands.
- `iog_offwindow_charge` starts a force only if the current dispatch has source
  `smart` (case-insensitive).
- The current dispatch is the `planned_dispatches` entry of the dispatching
  binary_sensor with `start <= now < end`.
- No matching entry, or any other source (boost, unknown), means no force.
- Stop, ownership, owner-stop and re-arm logic are unchanged. The discharge
  pause guard is unchanged.

## Alternatives considered
- **Keep the force for every dispatch** — rejected; it charges at peak rate.
- **Block only `boost`** — rejected; an unknown source would still charge.

## Consequences
- Live check 21-11-26: `planned_dispatches` was empty. Entries in
  `completed_dispatches` all read source `unknown`. The exact string for a real
  smart dispatch is not seen yet; the match is `smart`. If Octopus uses another
  word, no force starts (safe side). Check the next live dispatch.
- A dispatch absent from `planned_dispatches` while it runs gets no force.
