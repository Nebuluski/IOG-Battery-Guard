import importlib.util
import pathlib

import pytest

yaml = pytest.importorskip("yaml")

PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ha_inverter_card.py"
spec = importlib.util.spec_from_file_location("ha_inverter_card", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_read_env_missing_and_empty(tmp_path):
    assert mod.read_env(tmp_path / "none.env") == {}
    empty = tmp_path / "e.env"
    empty.write_text("")
    assert mod.read_env(empty) == {}


def test_read_env_parses(tmp_path):
    f = tmp_path / "x.env"
    f.write_text("# c\nHA_BASE_URL=http://h:8123\nHA_TOKEN=\n")
    assert mod.read_env(f) == {"HA_BASE_URL": "http://h:8123", "HA_TOKEN": ""}


def test_main_without_token_exits_nonzero(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "ENV", tmp_path / "missing.env")
    assert mod.main([]) != 0


def test_yaml_files_load():
    assert mod.load_yaml("dashboard/inverter-controls.yaml")
    for sid in mod.SCRIPT_IDS:
        assert "sequence" in mod.load_yaml(f"scripts/{sid}.yaml")[sid]


def test_insert_card_twice_does_not_stack():
    card = mod.load_yaml("dashboard/inverter-controls.yaml")
    conf = {
        "views": [
            {
                "path": "default_view",
                "cards": [{"type": "custom:givtcp-power-flow-card"}, {"type": "x"}],
            }
        ]
    }
    mod.insert_card(conf, card)
    mod.insert_card(conf, card)
    cards = conf["views"][0]["cards"]
    assert len(cards) == 3
    assert cards[1] == card
