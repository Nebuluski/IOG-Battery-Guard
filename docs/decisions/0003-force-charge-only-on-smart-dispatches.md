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
- Live check 20-11-26 and 21-11-26: `planned_dispatches` entries read source
  `SMART`. The live dispatch stayed in `planned_dispatches` while it ran.
  `completed_dispatches` entries read `unknown`, so the gate reads planned, not
  completed. The match is case-insensitive.
- A dispatch with no planned entry gets no force (safe side, by owner rule).
- Accepted: after an HA restart during a force, attributes may load late. The
  gate then fails and STOP cancels the force. The next 5-minute trigger restarts
  it. This is cost-safe.
- The force loop re-checks the SMART gate on each pass. A SMART dispatch that
  runs into a boost stops the re-arm, and the STOP logic ends the force.
