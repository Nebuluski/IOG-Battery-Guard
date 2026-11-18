import importlib.util
import pathlib

import pytest

yaml = pytest.importorskip("yaml")

PATH = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "ha_inverter_card.py"
spec = importlib.util.spec_from_file_location("ha_inverter_card", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
REAL_STATE = mod.Ha.state


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


def test_insert_card_no_default_view_raises():
    with pytest.raises(ValueError, match="default_view"):
        mod.insert_card({"views": [{"path": "other", "cards": []}]}, {"type": "x"})
    with pytest.raises(ValueError, match="default_view"):
        mod.insert_card({}, {"type": "x"})


def test_insert_card_sections_view_refused():
    conf = {"views": [{"path": "default_view", "sections": []}]}
    with pytest.raises(ValueError, match="cards"):
        mod.insert_card(conf, {"type": "x"})


class FakeHa:
    states = {}
    get_states_reply = None

    def __init__(self, base, token):
        self.ws = type("W", (), {"close": lambda self: None})()
        self.calls = 0

    def call(self, msg):
        if msg["type"] == "get_states":
            if FakeHa.get_states_reply is not None:
                return FakeHa.get_states_reply
            return {
                "success": True,
                "result": [{"entity_id": k, "state": v} for k, v in FakeHa.states.items()],
            }
        if msg["type"] == "lovelace/config":
            return {"success": True, "result": {"views": [{"path": "default_view", "cards": []}]}}
        return {"success": True, "result": []}

    def rest(self, method, path, body=None):
        return 200

    def state(self, eid):
        return REAL_STATE(self, eid)

    def lovelace(self, url_path):
        return self.call({"type": "lovelace/config"}).get("result")


@pytest.fixture
def fake_main(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("HA_BASE_URL=http://h:8123\nHA_TOKEN=t\n")
    monkeypatch.setattr(mod, "ENV", env)
    monkeypatch.setattr(mod, "Ha", FakeHa)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    FakeHa.get_states_reply = None
    FakeHa.states = {}
    return mod.main


def test_main_fails_when_force_entity_missing(fake_main, capsys):
    FakeHa.states = {mod.FC: "Normal"}
    assert fake_main(["--no-save"]) == 1
    assert "missing" in capsys.readouterr().err


def test_main_fails_when_all_entities_missing(fake_main):
    assert fake_main(["--no-save"]) == 1


def test_state_error_reply_raises():
    ha = FakeHa("h", "t")
    FakeHa.get_states_reply = {"success": False, "error": {"message": "boom"}}
    with pytest.raises(RuntimeError, match="get_states failed"):
        REAL_STATE(ha, mod.FC)
    FakeHa.get_states_reply = {"success": True}
    assert REAL_STATE(ha, mod.FC) is None


def test_main_fails_on_get_states_error(fake_main, capsys):
    FakeHa.get_states_reply = {"success": False, "error": {"message": "boom"}}
    assert fake_main(["--no-save"]) == 1
    assert "get_states failed" in capsys.readouterr().err


def test_main_passes_when_entities_present(fake_main):
    FakeHa.states = {mod.FC: "Normal", mod.FE: "Normal"}
    assert fake_main(["--no-save"]) == 0


def _no_ha(monkeypatch, tmp_path):
    """Fail the test if main reads .env or builds an Ha connection."""

    def boom(*a, **k):
        raise AssertionError("main touched .env or HA before parsing flags")

    monkeypatch.setattr(mod, "Ha", boom)
    monkeypatch.setattr(mod, "read_env", boom)


def test_main_help_exits_zero_without_ha(monkeypatch, tmp_path, capsys):
    _no_ha(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as e:
        mod.main(["--help"])
    assert e.value.code == 0
    assert "--no-save" in capsys.readouterr().out


def test_main_unknown_flag_exits_two_without_ha(monkeypatch, tmp_path, capsys):
    _no_ha(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as e:
        mod.main(["--bogus"])
    assert e.value.code == 2
    assert "--bogus" in capsys.readouterr().err
