# IOG Battery-Guard — step-by-step setup (newbie edition)

This guide takes you from your current Home Assistant (HA) to a working
automation that **stops your GivEnergy battery discharging while Octopus
Intelligent Go is charging cheaply, or while the Zappi charges the car**, then
puts it back to normal afterwards.

Follow the parts **in order**. Don't skip Part 0 — the automation can't work
until GivTCP is reinstalled and you've found your three entity IDs.

**Your setup (for reference):**
- Home Assistant: Supervised (you have the **Settings → Add-ons** store) — good.
- Battery: GivEnergy **Gen 1 hybrid 5 kW**, inverter IP **`10.0.30.10`**.
- Battery normally: **Eco mode**, with a **timed charge 23:30–05:30**.
- Octopus Energy integration: already installed and working — we leave it alone.

---

## How the automation behaves (plain English)

- Octopus's **"intelligent dispatching"** sensor turns **on** whenever IOG is
  giving you cheap power — both the nightly 23:30–05:30 window **and** any
  daytime "smart" slots it grabs to charge the car.
- The **Zappi power** sensor shows how many watts the car charger draws.
  Above **200 W** means "the car is charging".
- **Dispatch on, or Zappi above 200 W** → the automation starts a GivTCP
  **timed pause** of discharge: it picks **`60`** (minutes) on the
  *Temp Pause Discharge* control. The control then reads **`Running`**.
- When the 60 minutes run out, GivTCP sets the control back to **`Normal`**.
  If the cheap slot or the car charge is still on, the automation picks `60`
  again at once (re-arm).
- **Dispatch off AND Zappi below 200 W** → the automation picks **`Cancel`** →
  the pause ends and the battery is back to normal Eco.
- Your **overnight timed charge is never touched** — pausing *discharge* doesn't
  stop the battery *charging*. It never changes mode, reserve, slots, rates or
  force charge.
- It re-checks after an HA reboot and every 5 minutes.
- **Fail-safe:** a sensor that is *unavailable* never starts a pause and never
  ends one. If a pause runs out while a sensor is unavailable, it re-arms.

### The second automation: off-window charge (IOG-23)
- A dispatch **outside 23:30–05:30** (a daytime car charge) → it starts a GivTCP
  **timed force charge** on *Force Charge*, so the battery charges at the cheap
  rate too. The time is the minutes left in the dispatch, rounded up to the next
  option (2 … 180). With no end time it uses 30.
- If the force runs out and the dispatch is still on, it starts it again.
- **Dispatch off, or 23:30** → it cancels the force, but only a force it started.
  A force you start from the card is never cancelled.
- Press **Force stop** during the dispatch and it leaves the force alone until
  the next dispatch.
- It never touches the discharge pause. The guard above still wins.
- The battery stops at its charge target (92 %) or when full. That is correct.
- Decision: [ADR 0002](decisions/0002-force-charge-during-daytime-dispatch.md).

---

## Part 0 — Prerequisites

### Step 1 — Back up first (2 minutes, do not skip)
HA → **Settings → System → Backups → Create backup** (full). If anything goes
sideways later, you can restore in one click.

### Step 2 — Note your battery's normal state
Open the **GivEnergy app** and confirm it's in **Eco** with the overnight timed
charge. That's the "normal" we return to. Nothing to change here — just confirm.

### Step 3 — Uninstall GivTCP completely
1. HA → **Settings → Add-ons**.
2. Click **GivTCP** → **Uninstall**. Confirm.
3. (Optional clean-up) Still under Add-ons, if a *GivTCP repository* was added
   separately you can leave it — we'll reuse it to reinstall the latest version.

> Why uninstall/reinstall? To land on the **latest** GivTCP with the reliable
> local control entities this automation depends on.

### Step 4 — Reinstall GivTCP (latest) and point it at your inverter
1. HA → **Settings → Add-ons → Add-on Store** (bottom-right).
2. Find **GivTCP** in the list and click it. (If it isn't there: top-right
   **⋮ → Repositories**, add `https://github.com/britkat1980/giv_tcp-ha`, then
   reopen the store and find GivTCP.)
3. Click **Install** and wait for it to finish.
4. Open the add-on's **Configuration** tab and set:
   - **Inverter IP / `INVERTER_IP`** → `10.0.30.10`
   - **Number of inverters** → `1`
   - Leave **MQTT** on its default (the add-on's built-in broker is fine to
     start); make sure **HA discovery** / `HADISCOVERY` is **enabled** so the
     entities appear automatically.
   - Make sure **control is enabled** (sometimes called *Self Run* / *Control*
     / *self_run_loop*) — this is what creates the *writable* control entities
     we need, not just read-only sensors.
5. **Info** tab → turn on **Start on boot** and **Watchdog** → click **Start**.
6. **Log** tab → confirm it connects to `10.0.30.10` with no repeating errors.

### Step 5 — Find your THREE entity IDs (the important bit)
HA → **Developer Tools → States** (left sidebar; if hidden, enable *Advanced
Mode* in your user profile).

**(a) The Octopus dispatch sensor.** In the *Entity* filter box, type
`intelligent_dispatching`. You may see **several**. Newer versions of the
Octopus Energy integration make one per IOG device (for example your car),
like:

```
binary_sensor.octopus_energy_<octopus_device>_intelligent_dispatching
```

Pick the one whose state is **`on` or `off`** — not `unavailable`. Copy the
**full entity ID**.

**(b) The Zappi power sensor.** Clear the filter and type `zappi`. Pick the
one that reads live charge power, for example
`sensor.myenergi_zappi_<serial>_power_ct_internal_load`. Check its unit:
**`W`** means keep the `200` threshold. **`kW`** means change every `200` to
`0.2`.

**(c) The GivTCP pause control.** Clear the filter and type `pause`. GivTCP
3.6.14 has **no** untimed "battery pause mode" here. Use:

```
select.givtcp_<your-serial>_temp_pause_discharge
```

Its **Attributes → `options`** are: `Normal`, `Running`, `Cancel`, and minute
counts `2` … `180`. The automation uses `60` (start), `Cancel` (stop) and
reads `Normal` / `Running`.

### Step 6 — Sanity-check the control by hand
Set the pause control to **`2`** (two minutes) and watch the **GivEnergy app**:
within ~30–60 s the battery should stop discharging (0 W out) even if the house
is drawing power. The control reads `Running`. After two minutes it reads
`Normal` and discharge resumes. If that works, the automation will work. ✅

---

## Part 1 — Install the automation

### Step 7 — Put your real values into the YAML
Open `automations/iog_battery_guard.yaml` (in this repo) and **replace every
`<octopus_device>`** with the device part of your sensor (a). If your Zappi or
GivTCP serial differs, replace those ids too. Use Find-and-Replace so you don't
miss one — each id appears several times.

### Step 8 — Add it to Home Assistant
Use the deploy scripts (they read `HA_BASE_URL` and `HA_TOKEN` from `.env`):
1. `py -3 scripts/ha_inverter_card.py --no-save` — creates the two helpers the
   off-window automation needs (`input_boolean.iog_offwindow_owned` and
   `input_boolean.iog_offwindow_user_stop`).
2. `py -3 scripts/ha_push_automations.py --octopus-device <your device id> --dry-run`
   — prints the two automation ids. Nothing is sent.
3. Run the same command without `--dry-run`. It pushes both automations and
   reloads them. A non-zero exit code means an HTTP error.
4. If HA complains, check the entity ids from Step 7.

> By hand instead? **Settings → Automations & Scenes → + Create Automation →
> Edit in YAML**, paste each automation from its `- alias:` line down, and
> create the two helpers under **Settings → Devices & services → Helpers**.

### Step 9 — First test
1. **Developer Tools → YAML → Check Configuration** → expect *Configuration
   valid*.
2. Find the automation under **Settings → Automations**, open it, **⋮ → Run**.
   With no dispatch and no car charge it changes nothing (or cancels a running
   pause) — that's correct.
3. **Real test:** during the **23:30–05:30** window (sensor on), check the
   GivEnergy app shows the battery **not discharging**, and that after the
   window it resumes. Or temporarily prove the logic with the manual toggle from
   Step 6 while watching the automation's **Traces** (⋮ → Traces).

---

## Part 2 — Done / how this is tracked

This project is a ClaudeCoding workspace repo with its own Vikunja board and git
hooks. The automation + this guide are versioned here. Future tweaks follow the
repo workflow in `README.md` (card → `task-<id>` branch → task-ref commit).

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Save fails with "entity not found" | A placeholder wasn't replaced, or a typo in the entity ID. Re-copy from Developer Tools → States. |
| Battery still discharges during cheap slot | The dispatch sensor isn't turning `on` (check it in Dev Tools), or you picked an `unavailable` dispatch sensor in Step 5(a). |
| Battery never resumes | A sensor is `unavailable` (fail-safe keeps the pause), or the control is stuck — set it to `Cancel` by hand and check Traces. |
| Short discharge every 60 minutes during a long slot | The timed pause ran out; the re-arm follows within seconds. Normal. |
| Works at night, not on daytime dispatches | Normal — only happens when Octopus actually grants a smart slot; the sensor will be `on` when it does. |
| After an HA reboot it's in the wrong state | The startup + 5-min triggers fix this within 5 minutes; check the automation is **enabled**. |

---

## Appendix — fallback if there's no Battery-Pause select

If Step 5(c) found no `..._temp_pause_discharge` select, control discharge via the
**discharge-rate number** instead. Find it in Dev Tools → States (filter
`discharge`), e.g. `number.givtcp_<serial>_battery_discharge_rate` (watts) or a
`..._discharge_power_limit` (%). Then in the automation, swap the two
`select.select_option` actions for:

```yaml
# pause: stop discharge
- action: number.set_value
  target:
    entity_id: number.givtcp_SERIAL_battery_discharge_rate
  data:
    value: 0

# resume: restore full discharge (use the entity's normal max — often 2600 for a
# 5 kW Gen 1, or 100 if yours is a percentage limit; check its max attribute)
- action: number.set_value
  target:
    entity_id: number.givtcp_SERIAL_battery_discharge_rate
  data:
    value: 2600
```

Everything else (triggers, guard, structure) stays the same.
