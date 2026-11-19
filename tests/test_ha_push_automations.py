"""IOG-23: checks on scripts/ha_push_automations.py. No network: only the HTTP layer is mocked."""

import importlib.util
import pathlib

import pytest

pytest.importorskip("yaml")

PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ha_push_automations.py"
spec = importlib.util.spec_from_file_location("ha_push_automations", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DEV = "abc123"


def test_render_substitutes_device_everywhere():
    autos = mod.render(mod.SRC.read_text(encoding="utf-8"), DEV)
    assert [a["id"] for a in autos] == ["iog_battery_guard", "iog_offwindow_charge"]
    text = str(autos)
    assert "<octopus_device>" not in text
    assert f"binary_sensor.octopus_energy_{DEV}_intelligent_dispatching" in text


def test_render_empty_file_raises():
    with pytest.raises(ValueError):
        mod.render("", DEV)


def test_unknown_flag_exits_2():
    with pytest.raises(SystemExit) as e:
        mod.main(["--octopus-device", DEV, "--bogus"])
    assert e.value.code == 2


def test_missing_device_exits_2():
    with pytest.raises(SystemExit) as e:
        mod.main([])
    assert e.value.code == 2


def test_malformed_device_exits_2():
    assert mod.main(["--octopus-device", "<x y>"]) == 2


def test_dry_run_prints_ids_and_makes_no_call(monkeypatch, capsys):
    monkeypatch.setattr(mod, "post", lambda *a: pytest.fail("network used"))
    assert mod.main(["--octopus-device", DEV, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "iog_offwindow_charge" in out and "iog_battery_guard" in out


def test_no_token_exits_nonzero(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "ENV", tmp_path / "none.env")
    assert mod.main(["--octopus-device", DEV]) == 2


def _env(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text("HA_BASE_URL=http://ha:8123/\nHA_TOKEN=tok-secret\n")
    monkeypatch.setattr(mod, "ENV", f)


def test_push_posts_each_then_reloads_and_hides_token(monkeypatch, tmp_path, capsys):
    _env(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(mod, "post", lambda b, t, p, body: calls.append((b, p, body)) or 200)
    assert mod.main(["--octopus-device", DEV]) == 0
    assert [c[1] for c in calls] == [
        "/api/config/automation/config/iog_battery_guard",
        "/api/config/automation/config/iog_offwindow_charge",
        "/api/services/automation/reload",
    ]
    assert calls[0][0] == "http://ha:8123"
    assert "tok-secret" not in capsys.readouterr().out


def test_push_http_error_exits_1(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setattr(mod, "post", lambda b, t, p, body: 400 if "offwindow" in p else 200)
    assert mod.main(["--octopus-device", DEV]) == 1
