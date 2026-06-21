# IOG Battery-Guard — step-by-step setup (newbie edition)

This guide takes you from your current Home Assistant (HA) to a working
automation that **stops your GivEnergy battery discharging while Octopus
Intelligent Go is charging cheaply**, then puts it back to normal afterwards.

Follow the parts **in order**. Don't skip Part 0 — the automation can't work
until GivTCP is reinstalled and you've found your two entity IDs.

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
- **Sensor on**  → battery is told **"Pause Discharge"** (it stops feeding the
  house/car from stored energy; cheap grid covers it instead).
- **Sensor off** → battery is told **"Not Paused"** → back to normal Eco.
- Your **overnight timed charge is never touched** — pausing *discharge* doesn't
  stop the battery *charging*.
- It also self-corrects after an HA reboot and every 15 minutes, and does
  nothing if the Octopus sensor is temporarily unavailable.

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

### Step 5 — Find your TWO entity IDs (the important bit)
HA → **Developer Tools → States** (left sidebar; if hidden, enable *Advanced
Mode* in your user profile).

**(a) The Octopus dispatch sensor.** In the *Entity* filter box, type
`intelligent_dispatching`. You'll see something like:

```
binary_sensor.octopus_energy_A_12345678_intelligent_dispatching
```

Copy that **full entity ID** — yours has *your* account number, not `12345678`.

**(b) The GivTCP battery-pause control.** Clear the filter and type `pause`.
Look for a **`select.`** entity, e.g.:

```
select.givtcp_<your-serial>_battery_pause_mode
```

Click it and look at its **Attributes → `options`** — note the **exact** words
it offers. You're looking for the one that means *stop discharging* (commonly
**`Pause Discharge`**) and the one that means *normal* (commonly
**`Not Paused`**). Write both down exactly, capitals and spaces included.

> **No `pause` select exists?** Some Gen 1 firmware doesn't expose Battery
> Pause. In that case use the **fallback** in the Appendix (set discharge rate
> to 0) — everything else in this guide is identical.

### Step 6 — Sanity-check the control by hand
Still in **Developer Tools → States** (or via the entity's dialog), set the
pause select to **Pause Discharge** and watch the **GivEnergy app**: within
~30–60 s the battery should stop discharging (0 W out) even if the house is
drawing power. Set it back to **Not Paused** and confirm discharge resumes.
If that works, the automation will work. ✅

---

## Part 1 — Install the automation

### Step 7 — Put your real values into the YAML
Open `automations/iog_battery_guard.yaml` (in this repo) and **replace every
occurrence** of:
- `binary_sensor.octopus_energy_A_12345678_intelligent_dispatching` → your **(a)**
- `select.givtcp_SERIAL_battery_pause_mode` → your **(b)**
- the two `option:` words (`"Pause Discharge"` / `"Not Paused"`) → the exact
  words from Step 5, **if** yours differ.

Tip: use Find-and-Replace so you don't miss one — the sensor ID appears several
times and they must all match.

### Step 8 — Add it to Home Assistant
Easiest route (UI, validates as you go):
1. HA → **Settings → Automations & Scenes → + Create Automation → Skip / Start
   with an empty automation**.
2. Top-right **⋮ → Edit in YAML**.
3. Delete what's there and **paste the contents of your edited
   `iog_battery_guard.yaml`** — but paste **from the `- alias:` line down**
   (don't paste the `#` comment header; it's just notes). The pasted block must
   start at `- alias:`.
4. **Save**. If HA complains, it'll point at the line — usually a leftover
   placeholder or a mismatched option word.

> Prefer files? If your `configuration.yaml` has `automation: !include
> automations.yaml`, paste the same block into `automations.yaml` instead, then
> **Developer Tools → YAML → Check Configuration**, then **Reload Automations**.

### Step 9 — First test
1. **Developer Tools → YAML → Check Configuration** → expect *Configuration
   valid*.
2. Find the automation under **Settings → Automations**, open it, **⋮ → Run**.
   With no dispatch active it should leave the battery alone (or un-pause it) —
   that's correct.
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
| Battery still discharges during cheap slot | The dispatch sensor isn't turning `on` (check it in Dev Tools), or the option word doesn't match GivTCP's exactly (check the select's `options`). |
| Battery never resumes | The "off" option word is wrong, or the select got stuck — set it to `Not Paused` by hand and check Traces. |
| Works at night, not on daytime dispatches | Normal — only happens when Octopus actually grants a smart slot; the sensor will be `on` when it does. |
| After an HA reboot it's in the wrong state | The startup + 15-min triggers fix this within 15 minutes; check the automation is **enabled**. |

---

## Appendix — fallback if there's no Battery-Pause select

If Step 5(b) found no `..._battery_pause_mode` select, control discharge via the
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
