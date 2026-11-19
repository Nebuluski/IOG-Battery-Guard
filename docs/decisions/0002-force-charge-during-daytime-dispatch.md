# 0002 — Force charge the battery during a daytime IOG dispatch

- **Date:** 2026-11-19
- **Status:** Accepted
- **Deciders:** Owner (option a, 19-11-26), Claude session

## Context
An IOG dispatch can run outside the 23:30-05:30 window to charge the car. The
battery guard pauses discharge then, so the battery only holds. It does not
charge, though the import is at the cheap rate. Card: IOG-23.

## Decision
A second automation, `iog_offwindow_charge`, in `automations/iog_battery_guard.yaml`:
- Dispatch on and time outside 23:30-05:30 -> pick a timed force charge on
  `select.givtcp_sd2145g043_force_charge`. The length is the minutes to the
  dispatch `current_end`, rounded up to the next select option (2 ... 180).
  With no `current_end` it uses 30.
- GivTCP ends the force at its timer. If the dispatch is still on, the
  automation re-arms it.
- Dispatch off, or 23:30 -> cancel the force, but only one this run started.
- A force the owner started is never replaced or cancelled. Force stop from the
  owner ("Cancel") ends the management for that dispatch.
- It never touches the discharge pause. The guard is unchanged and still wins.

## Alternatives considered
- **Use the card script `script.iog_force_charge`** — rejected; it reads the
  owner's duration helper, which must stay at his default.
- **Untimed force via mode/slots** — rejected; a missed stop leaves the battery
  in charge mode. A timed force ends by itself.
- **Keep the force past 23:30** — rejected; the night schedule owns the window.

## Consequences
- Ownership lives in the automation run. After an HA restart mid-dispatch, a
  running force is not cancelled at dispatch end; GivTCP times it out.
- Charging can stop at the inverter charge target (92 %). That is accepted.
- Deploy is by hand, like the guard (setup guide Part 1); no script pushes
  automations yet.
