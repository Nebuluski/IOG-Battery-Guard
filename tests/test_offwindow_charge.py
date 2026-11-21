"""IOG-23: checks on the real automations/iog_battery_guard.yaml (off-window charge)."""

import datetime
import json
import pathlib

import pytest

yaml = pytest.importorskip("yaml")

PATH = pathlib.Path(__file__).resolve().parent.parent / "automations" / "iog_battery_guard.yaml"
DISPATCH = "binary_sensor.octopus_energy_<octopus_device>_intelligent_dispatching"
FC = "select.givtcp_sd2145g043_force_charge"
OWNED = "input_boolean.iog_offwindow_owned"
USER_STOP = "input_boolean.iog_offwindow_user_stop"
PAUSE = "select.givtcp_sd2145g043_temp_pause_discharge"
# Options the live GivTCP force charge select offers (read from HA, 19-11-26).
FORCE_OPTIONS = ["Normal", "Running", "Cancel"] + [
    str(m) for m in (2, 5, 10, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180)
]


@pytest.fixture(scope="module")
def autos():
    data = yaml.safe_load(PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data, "automation file is empty"
    return {a["id"]: a for a in data}


@pytest.fixture(scope="module")
def off(autos):
    return autos["iog_offwindow_charge"]


def walk(node):
    """Yield every dict in a nested YAML tree."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def find_mins_template(off):
    for d in walk(off["actions"]):
        if isinstance(d.get("variables"), dict) and "mins" in d["variables"]:
            return d["variables"]["mins"]
    raise AssertionError("no mins template")


def test_both_automations_present(autos):
    assert set(autos) == {"iog_battery_guard", "iog_offwindow_charge"}


def test_guard_never_touches_force(autos):
    assert "force_charge" not in json.dumps(autos["iog_battery_guard"])


def test_offwindow_never_touches_pause(off):
    assert PAUSE not in json.dumps(off)


def test_offwindow_triggers(off):
    trig = off["triggers"]
    assert {"trigger": "state", "entity_id": DISPATCH, "to": "on"} in trig
    assert {"trigger": "homeassistant", "event": "start"} in trig
    assert {"trigger": "time_pattern", "minutes": "/5"} in trig
    assert {"trigger": "time", "at": "05:30:00"} in trig
    assert off["mode"] == "single"


def test_offwindow_needs_dispatch_on(off):
    conds = off["actions"][0]["if"]
    assert {"condition": "state", "entity_id": DISPATCH, "state": "on"} in conds
    assert {"condition": "state", "entity_id": USER_STOP, "state": "off"} in conds


def test_wait_ends_on_dispatch_off_and_window_start(off):
    waits = [d for d in walk(off["actions"]) if "wait_for_trigger" in d]
    assert len(waits) == 1
    w = waits[0]
    assert {"trigger": "state", "entity_id": DISPATCH, "to": "off"} in w["wait_for_trigger"]
    assert {"trigger": "time", "at": "23:30:00"} in w["wait_for_trigger"]
    assert w["timeout"] and w["continue_on_timeout"] is True


def test_selected_options_exist_on_givtcp(off):
    for d in walk(off["actions"]):
        if d.get("action") == "select.select_option":
            assert d["target"]["entity_id"] == FC
            opt = d["data"]["option"]
            assert opt in FORCE_OPTIONS or opt == "{{ mins }}"
    mins = find_mins_template(off)
    start = mins.index("[", mins.index("set fit"))
    for m in mins[start + 1 : mins.index("]", start)].split(","):
        assert m.strip() in FORCE_OPTIONS


def test_cancel_only_when_owned_helper_is_on(off):
    stop = off["actions"][1]
    assert {"condition": "state", "entity_id": OWNED, "state": "on"} in stop["if"]
    text = json.dumps(stop["then"])
    assert '"Cancel"' in text
    assert "input_boolean.turn_off" in text and OWNED in text


def test_state_lives_in_helpers_not_variables(off):
    names = set()
    for d in walk(off["actions"]):
        names |= set(d.get("variables") or {})
    assert not names & {"owned", "user_stop"}
    text = json.dumps(off["actions"])
    assert OWNED in text and USER_STOP in text


def test_owner_stop_is_persisted_and_blocks_runs(off):
    first = off["actions"][0]
    off_cond = {"condition": "state", "entity_id": USER_STOP, "state": "off"}
    assert off_cond in first["if"]
    assert off_cond in first["then"][0]["repeat"]["while"]
    sets = [
        d
        for d in walk(off["actions"])
        if d.get("action") == "input_boolean.turn_on" and d["target"]["entity_id"] == USER_STOP
    ]
    assert sets, "owner Cancel must set the user_stop helper"


def test_user_stop_cleared_on_dispatch_off(off):
    last = off["actions"][-1]
    assert {"condition": "state", "entity_id": DISPATCH, "state": "off"} in last["if"]
    assert last["then"][0]["action"] == "input_boolean.turn_off"
    assert last["then"][0]["target"]["entity_id"] == USER_STOP
    assert {"trigger": "state", "entity_id": DISPATCH, "to": "off"} in off["triggers"]


def test_ownership_set_before_force_and_failure_notified(off):
    steps = None
    for d in walk(off["actions"]):
        seq = d.get("sequence")
        if isinstance(seq, list) and any(
            isinstance(x, dict) and x.get("action") == "select.select_option" for x in seq
        ):
            steps = seq
            break
    assert steps is not None
    acts = [x.get("action") for x in steps]
    assert acts.index("input_boolean.turn_on") < acts.index("select.select_option")
    assert steps[acts.index("select.select_option")]["continue_on_error"] is True
    assert "persistent_notification.create" in json.dumps(steps)


# ---- render the real templates with Jinja2 -------------------------------------------

NOW = datetime.datetime(2026, 11, 19, 12, 0, tzinfo=datetime.timezone.utc)


def render(tpl, now=NOW, current_end=None):
    jinja2 = pytest.importorskip("jinja2")
    env = jinja2.Environment()
    env.globals.update(
        now=lambda: now,
        as_timestamp=lambda v, default=None: (
            v.timestamp()
            if isinstance(v, datetime.datetime)
            else datetime.datetime.fromisoformat(v).timestamp()
            if v
            else default
        ),
        state_attr=lambda e, a: current_end,
        is_state=lambda e, s: True,
    )
    return env.from_string(tpl).render(user_stop=False).strip()


@pytest.mark.parametrize(
    "end_min,want",
    [(None, "30"), (1, "2"), (30, "30"), (31, "45"), (47, "60"), (179, "180"), (400, "180")],
)
def test_mins_rounds_up_to_an_option(off, end_min, want):
    end = None if end_min is None else (NOW + datetime.timedelta(minutes=end_min)).isoformat()
    assert render(find_mins_template(off), current_end=end) == want


@pytest.mark.parametrize(
    "hhmm,outside",
    [("12:00", True), ("05:30", True), ("23:29", True), ("23:30", False), ("05:29", False)],
)
def test_window_check(off, hhmm, outside):
    h, m = map(int, hhmm.split(":"))
    now = NOW.replace(hour=h, minute=m)
    cond = off["actions"][0]["if"][1]["value_template"]
    loop = off["actions"][0]["then"][0]["repeat"]["while"][1]["value_template"]
    assert render(cond, now=now) == str(outside)
    assert render(loop, now=now) == str(outside)


# ---- IOG-24: force only for a SMART dispatch ------------------------------------------


def ha_as_timestamp(v, default=None):
    """Like HA: a datetime or a parsable ISO string gives a timestamp, else the default."""
    if isinstance(v, datetime.datetime):
        return v.timestamp()
    if isinstance(v, str):
        try:
            return datetime.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return default
    return default


def render_smart(tpl, planned, now=NOW):
    jinja2 = pytest.importorskip("jinja2")
    env = jinja2.Environment()
    env.globals.update(
        now=lambda: now,
        as_timestamp=ha_as_timestamp,
        state_attr=lambda e, a: planned if a == "planned_dispatches" else None,
    )
    return env.from_string(tpl).render().strip()


def smart_template(off):
    conds = off["actions"][0]["if"]
    found = [c for c in conds if "planned_dispatches" in c.get("value_template", "")]
    assert len(found) == 1, "start path must hold one source check"
    return found[0]["value_template"]


def entry(source, start_min=-10, end_min=20):
    return {
        "source": source,
        "start": (NOW + datetime.timedelta(minutes=start_min)).isoformat(),
        "end": (NOW + datetime.timedelta(minutes=end_min)).isoformat(),
        "charge_in_kwh": -1.0,
    }


@pytest.mark.parametrize(
    "planned,want",
    [
        ([entry("smart")], "True"),
        ([entry("Smart")], "True"),
        ([entry("boost")], "False"),
        ([entry("unknown")], "False"),
        ([entry(None)], "False"),
        ([], "False"),
        (None, "False"),
        ([entry("smart", 10, 40)], "False"),  # future entry, not current
        ([entry("smart", -40, -10)], "False"),  # past entry
        ([entry("boost"), entry("smart")], "True"),
        ([entry("smart", 10, 40), entry("boost")], "False"),
    ],
)
def test_force_only_for_smart_current_dispatch(off, planned, want):
    assert render_smart(smart_template(off), planned) == want


def aware(minutes):
    return NOW + datetime.timedelta(minutes=minutes)


@pytest.mark.parametrize(
    "planned,want",
    [
        ([{"source": "SMART", "start": aware(-10), "end": aware(20)}], "True"),
        ([{"source": "SMART", "start": aware(10), "end": aware(20)}], "False"),
        ([{"start": aware(-10), "end": aware(20)}], "False"),  # no source
        ([{"source": "smart", "end": aware(20)}], "False"),  # no start
        ([{"source": "smart", "start": aware(-10)}], "False"),  # no end
        ([{"source": "smart", "start": "bad", "end": "worse"}], "False"),
        (
            [
                {
                    "source": "smart",
                    "start": "2026-11-19T11:50:00Z",
                    "end": "2026-11-19T12:20:00Z",
                }
            ],
            "True",
        ),
        (
            [{"source": "smart", "start": "2026-11-19T12:10:00Z", "end": "2026-11-19T12:20:00Z"}],
            "False",
        ),
    ],
)
def test_smart_gate_edge_entries(off, planned, want):
    assert render_smart(smart_template(off), planned) == want


def test_loop_rechecks_same_smart_gate(off):
    first = off["actions"][0]
    loop_conds = first["then"][0]["repeat"]["while"]
    gates = [c for c in loop_conds if "planned_dispatches" in c.get("value_template", "")]
    assert len(gates) == 1, "loop must hold the SMART gate"
    assert gates[0]["value_template"] == smart_template(off)


def test_loop_gate_fails_when_current_entry_becomes_boost(off):
    first = off["actions"][0]
    loop_gate = [
        c
        for c in first["then"][0]["repeat"]["while"]
        if "planned_dispatches" in c.get("value_template", "")
    ][0]["value_template"]
    assert render_smart(loop_gate, [entry("smart")]) == "True"
    assert render_smart(loop_gate, [entry("boost")]) == "False"


def test_smart_gate_is_on_start_path_only(off):
    first = off["actions"][0]
    assert any("planned_dispatches" in c.get("value_template", "") for c in first["if"])
    # stop and ownership logic stay ungated so a running force still ends
    assert "planned_dispatches" not in json.dumps(off["actions"][1:])
