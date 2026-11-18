# Inverter control card

Decision: [ADR 0001](decisions/0001-ha-dashboard-and-inverter-controls.md).

## What the controls do
- **Mode and reserve** — set the inverter mode and battery reserve. Acts on tap.
- **Charge / discharge slots** — set the slot times.
- **Force charge / Force export** — ask first, then run for the minutes in
  `input_select.iog_force_duration` (default 30). GivTCP stops it and restores
  the old mode. A second force does nothing while one runs.
- **Force stop** — cancels a running force.
- **Pause and rate limits** — pause the battery, set charge/discharge rate.

## Files
- `ha/dashboard/inverter-controls.yaml` — the card.
- `ha/scripts/iog_force_*.yaml` — the three scripts (each has a `dry_run` field).
- `ha/helpers/input_select_iog_force_duration.yaml` — the duration helper.

## Rebuild
1. Copy `.env.example` to `.env`. Set `HA_TOKEN` (long-lived token).
2. `pip install websocket-client pyyaml`
3. `py -3 scripts/ha_inverter_card.py` (add `--no-save` to skip the dashboard save).

The script is safe to run twice. It exits non-zero on failure. It never prints the token.

## Backup and restore
Before each save, the script writes the old dashboard to
`ha/backups/lovelace_default_<time>.json` (gitignored). To restore: in HA open
Home, edit, raw configuration editor, and paste the JSON content.
