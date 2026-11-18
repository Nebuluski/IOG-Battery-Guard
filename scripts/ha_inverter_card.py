"""IOG-21: push the iog_ helper + scripts to HA and put the inverter control card on Home.

Usage: py -3 scripts/ha_inverter_card.py [--no-save] [--help]
Reads HA_BASE_URL and HA_TOKEN from <repo root>/.env. Reads YAML from ha/.
Never prints the token. Safe to run twice: the helper is created only if missing,
scripts are overwritten, and the card is replaced, not stacked.
Needs: pip install websocket-client pyyaml
"""

import argparse
import datetime
import json
import pathlib
import sys
import time
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
HA_DIR = ROOT / "ha"
ENV = ROOT / ".env"
BACKUPS = ROOT / "ha" / "backups"
MARK = "Inverter controls"
SCRIPT_IDS = ("iog_force_charge", "iog_force_export", "iog_force_stop")
P = "givtcp_sd2145g043"
FC, FE = f"select.{P}_force_charge", f"select.{P}_force_export"


def read_env(path):
    """Return KEY=VALUE pairs from an env file. Empty or missing file gives {}."""
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def load_yaml(rel):
    return yaml.safe_load((HA_DIR / rel).read_text(encoding="utf-8"))


def insert_card(conf, card):
    """Put card under the GivTCP power overview on the default view. Replaces an old copy."""
    view = next((v for v in conf.get("views") or [] if v.get("path") == "default_view"), None)
    if view is None:
        raise ValueError("no view with path 'default_view' in the dashboard")
    if view.get("cards") is None:
        raise ValueError("default_view has no 'cards' key (sections view?); refusing to edit it")
    cards = [
        c
        for c in view["cards"]
        if not (
            c.get("type") == "vertical-stack" and (c.get("cards") or [{}])[0].get("heading") == MARK
        )
    ]
    givtcp = [
        i for i, c in enumerate(cards[:4]) if str(c.get("type", "")).startswith("custom:givtcp-")
    ]
    idx = max(givtcp) if givtcp else 0
    cards.insert(idx + 1, card)
    view["cards"] = cards
    return idx + 1


class Ha:
    def __init__(self, base, token):
        import websocket

        self.base, self.token, self.n = base, token, 0
        self.ws = websocket.create_connection(
            base.replace("http", "ws", 1) + "/api/websocket", timeout=30
        )
        self.ws.recv()
        self.ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(self.ws.recv())["type"] != "auth_ok":
            raise RuntimeError("HA auth failed")

    def call(self, msg):
        self.n += 1
        msg["id"] = self.n
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.n:
                return r

    def rest(self, method, path, body=None):
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status

    def state(self, eid):
        r = self.call({"type": "get_states"})
        if not r.get("success"):
            raise RuntimeError(f"get_states failed: {r.get('error')}")
        for s in r.get("result") or []:
            if s["entity_id"] == eid:
                return s["state"]
        return None

    def lovelace(self, url_path):
        m = {"type": "lovelace/config"}
        if url_path:
            m["url_path"] = url_path
        return self.call(m).get("result")

    def save(self, url_path, conf):
        m = {"type": "lovelace/config/save", "config": conf}
        if url_path:
            m["url_path"] = url_path
        return self.call(m)


def parse_args(argv):
    """Parse flags. An unknown flag exits 2; --help exits 0. Both happen before any I/O."""
    ap = argparse.ArgumentParser(
        prog="ha_inverter_card.py",
        description="Push the iog_ helper + scripts to HA and put the inverter card on Home.",
    )
    ap.add_argument("--no-save", action="store_true", help="skip the dashboard backup and save")
    return ap.parse_args(argv)


def main(argv):
    no_save = parse_args(argv).no_save
    cfg = read_env(ENV)
    base, token = cfg.get("HA_BASE_URL", "").rstrip("/"), cfg.get("HA_TOKEN", "")
    if not base or not token:
        print("error: set HA_BASE_URL and HA_TOKEN in .env", file=sys.stderr)
        return 2
    ok = True
    ha = Ha(base, token)

    # 1. helper (created only if missing)
    helper = load_yaml("helpers/input_select_iog_force_duration.yaml")["iog_force_duration"]
    existing = ha.call({"type": "input_select/list"}).get("result") or []
    if any(
        h.get("id") == "iog_force_duration" or h.get("name") == helper["name"] for h in existing
    ):
        print("helper: exists (left as is)")
    else:
        r = ha.call({"type": "input_select/create", **helper})
        print("helper: created" if r.get("success") else f"helper: FAILED {r.get('error')}")
        ok = ok and bool(r.get("success"))

    # 2. scripts (overwritten)
    for sid in SCRIPT_IDS:
        body = load_yaml(f"scripts/{sid}.yaml")[sid]
        st = ha.rest("POST", f"/api/config/script/config/{sid}", body)
        print(f"script {sid}: HTTP {st}")
        ok = ok and st == 200
    time.sleep(3)

    # 3. dry runs: no inverter change
    try:
        before = (ha.state(FC), ha.state(FE))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if None in before:
        print(
            f"error: force select entity missing ({FC} / {FE}); cannot check state", file=sys.stderr
        )
        return 1
    for sid in SCRIPT_IDS:
        r = ha.call(
            {
                "type": "call_service",
                "domain": "script",
                "service": sid,
                "service_data": {"dry_run": True},
            }
        )
        print(f"dry run {sid}: success={r.get('success')} {r.get('error', '')}")
        ok = ok and bool(r.get("success"))
    time.sleep(2)
    try:
        after = (ha.state(FC), ha.state(FE))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if None in after:
        print("error: force select entity missing after dry runs", file=sys.stderr)
        return 1
    print(f"force selects unchanged={before == after}")
    ok = ok and before == after

    # 4. card (backup first)
    card = load_yaml("dashboard/inverter-controls.yaml")
    d0 = ha.lovelace(None)
    if not d0 or "views" not in d0:
        print("error: dashboard config empty or not storage mode", file=sys.stderr)
        return 1
    if not no_save:
        BACKUPS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        (BACKUPS / f"lovelace_default_{stamp}.json").write_text(
            json.dumps(d0, indent=1), encoding="utf-8"
        )
        try:
            pos = insert_card(d0, card)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        r = ha.save(None, d0)
        print(f"saved default: success={r.get('success')} card at index {pos} {r.get('error', '')}")
        ok = ok and bool(r.get("success"))
        d1 = ha.lovelace("lovelace")
        if d1 and json.dumps(d1, sort_keys=True) != json.dumps(ha.lovelace(None), sort_keys=True):
            (BACKUPS / f"lovelace_lovelace_{stamp}.json").write_text(
                json.dumps(d1, indent=1), encoding="utf-8"
            )
            try:
                pos = insert_card(d1, card)
            except ValueError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            r = ha.save("lovelace", d1)
            print(f"saved lovelace (separate store): success={r.get('success')} index {pos}")
            ok = ok and bool(r.get("success"))
        print("backup stamp:", stamp)
    ha.ws.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
