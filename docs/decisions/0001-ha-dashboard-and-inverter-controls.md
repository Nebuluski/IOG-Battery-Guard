# 0001 — HA dashboard and inverter controls

- **Date:** 2026-11-18
- **Status:** Accepted
- **Deciders:** Owner (choices 18-11-26), Claude session

## Context
The owner wants the GivEnergy power overview in Home Assistant plus a card to
control the inverter. This is wider than the original remit (the dispatch
battery guard). Card: IOG-21.

## Decision
The IOG remit widens to the GivEnergy power overview and an inverter control
card in HA (`ha/` folder). Owner choices:
- Controls: mode and reserve, charge/discharge slots, force charge/export,
  pause and rate limits.
- The battery guard always wins. The guard is not installed yet, so the card
  only shows its status.
- Placement: under the power overview on the Home view.
- Force buttons ask for confirmation and stop by themselves (default 30 min,
  GivTCP force select timer).
- HA access uses its own long-lived token, `HA_TOKEN`, in `.env`.

## Alternatives considered
- **Separate dashboard** — rejected; the owner wants one Home view.
- **Force with no timer** — rejected; a forgotten force would drain or fill the battery.

## Consequences
- Mode, reserve and pause act on tap with no confirm. The owner chose confirm
  for force only.
- The card needs `scripts/ha_inverter_card.py` to rebuild it. It backs up the
  dashboard before each save.
- When the guard is installed, add an override so the guard blocks the card.
