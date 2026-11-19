"""IOG-23: push the automations in automations/iog_battery_guard.yaml to Home Assistant.

Usage: py -3 scripts/ha_push_automations.py --octopus-device ID [--dry-run] [--help]
Reads HA_BASE_URL and HA_TOKEN from <repo root>/.env. Never prints the token.
Safe to run twice: each automation is overwritten by id. Then it calls automation.reload.
Run ha_inverter_card.py first: the off-window automation needs its two input_boolean helpers.
Exit 0 on success, 1 on any HTTP error, 2 on bad flags or a missing .env value.
"""

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "automations" / "iog_battery_guard.yaml"
ENV = ROOT / ".env"
PLACEHOLDER = "<octopus_device>"


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


def render(text, device):
    """Parse the YAML with the placeholder replaced. Returns a list of automations."""
    data = yaml.safe_load(text.replace(PLACEHOLDER, device))
    if not isinstance(data, list) or not data:
        raise ValueError("automation file holds no automations")
    for a in data:
        if not a.get("id"):
            raise ValueError(f"automation without id: {a.get('alias')}")
    return data


def post(base, token, path, body):
    """POST JSON to HA. Returns the HTTP status; an HTTP error status is returned, not raised."""
    req = urllib.request.Request(
        base + path,
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def parse_args(argv):
    """Parse flags. An unknown flag exits 2; --help exits 0. Both happen before any I/O."""
    ap = argparse.ArgumentParser(
        prog="ha_push_automations.py",
        description="Push automations/iog_battery_guard.yaml to HA and reload automations.",
    )
    ap.add_argument(
        "--octopus-device",
        required=True,
        help="Octopus device id in the dispatching binary_sensor entity id",
    )
    ap.add_argument("--dry-run", action="store_true", help="print ids and aliases only")
    return ap.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    device = args.octopus_device.strip()
    if not device or any(c in device for c in "<> /"):
        print("error: --octopus-device is empty or malformed", file=sys.stderr)
        return 2
    autos = render(SRC.read_text(encoding="utf-8"), device)
    if args.dry_run:
        for a in autos:
            print(f"{a['id']}: {a.get('alias', '')}")
        return 0
    cfg = read_env(ENV)
    base, token = cfg.get("HA_BASE_URL", "").rstrip("/"), cfg.get("HA_TOKEN", "")
    if not base or not token:
        print("error: set HA_BASE_URL and HA_TOKEN in .env", file=sys.stderr)
        return 2
    ok = True
    for a in autos:
        st = post(base, token, f"/api/config/automation/config/{a['id']}", a)
        print(f"automation {a['id']}: HTTP {st}")
        ok = ok and st == 200
    st = post(base, token, "/api/services/automation/reload", {})
    print(f"automation.reload: HTTP {st}")
    ok = ok and st == 200
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
