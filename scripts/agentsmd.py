#!/usr/bin/env python3
"""agentsmd.py -- keep every AGENTS.md a generated copy of its CLAUDE.md.

Codex reads AGENTS.md, not CLAUDE.md (card GEN-80). CLAUDE.md stays the source.
For each CLAUDE.md that git tracks (skipping paths under `.claude/`), AGENTS.md
beside it = a fixed header (4 comment lines, the last one a sha256 of the
CLAUDE.md text) + a blank line + the CLAUDE.md text verbatim.

Usage:
  agentsmd.py                Write mode: CLAUDE.md always wins; create or update
                             each AGENTS.md.
  agentsmd.py --check        Write nothing. Exit 1 if any AGENTS.md is missing
                             or differs.
  agentsmd.py --sync         Two-way, per pair, using the header hash:
                             CLAUDE.md changed -> regenerate AGENTS.md;
                             AGENTS.md edited  -> write its body back into
                             CLAUDE.md (BOM and dominant line ending kept),
                             then regenerate. Refused (exit 1, nothing written)
                             when the body is empty or under half the size of
                             CLAUDE.md. Both changed and different -> CONFLICT,
                             nothing written for that pair, exit 1.
  agentsmd.py --force        Also overwrite an AGENTS.md that has no GENERATED
                             header (hand-written). Without it such a file is
                             never touched and the run exits 1.
  agentsmd.py --root PATH    Operate on PATH instead of the current directory.

Exit codes: 0 = ok (or no tracked CLAUDE.md: a no-op note), 1 = --check found
drift, a conflict, a refusal or a hand-written AGENTS.md, 2 = git missing, PATH
is not a git repo, an unreadable or non-UTF-8 file, or bad flags.

Every write goes to a temp file in the same folder, then os.replace.
An AGENTS.md with no CLAUDE.md beside it is never removed. --check warns about
one that starts with the GENERATED header (an orphan) and still exits 0.
Standard library only. ASCII-only output.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile

HEAD3 = (
    "<!-- GENERATED from CLAUDE.md by scripts/agentsmd.py. Do not edit. "
    "Edit CLAUDE.md, then run: python scripts/agentsmd.py -->\n"
    "<!-- Codex: these are the same rules Claude follows in this repo. "
    "Where they name a Claude tool, use your nearest equivalent. -->\n"
    "<!-- Global and workspace rules: ~/.codex/AGENTS.md. -->\n"
)
HASH_RE = re.compile(r"<!-- source-sha256: ([0-9a-f]{64}) -->")
MARKER = "<!-- GENERATED from CLAUDE.md by scripts/agentsmd.py."
FIX = "python scripts/agentsmd.py --sync"
MIN_BODY_RATIO = 0.5


class Fatal(Exception):
    """A one-line error: print it and exit 2."""


class Doc:
    """A text file read strictly as UTF-8, normalised to LF."""

    def __init__(self, text, bom, crlf):
        self.text = text
        self.bom = bom
        self.crlf = crlf


def git_ls_files(root):
    """Tracked paths ('/'-separated, relative to root). Raises Fatal."""
    try:
        proc = subprocess.run(
            ["git", "-C", root, "ls-files", "-z", "--cached"],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise Fatal(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise Fatal(f"not a git repo or git failed: {err or root}")
    out = proc.stdout.decode("utf-8", "replace")
    return [p for p in out.split("\0") if p]


def find_claude_files(tracked):
    """Tracked CLAUDE.md paths, excluding anything under .claude/."""
    found = []
    for p in tracked:
        parts = p.split("/")
        if parts[-1] != "CLAUDE.md" or ".claude" in parts[:-1]:
            continue
        found.append(p)
    return sorted(found)


def load(path, required):
    """Read a file strictly. None if missing and not required. Raises Fatal."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        if required:
            raise Fatal(f"tracked file is missing on disk: {path}") from None
        return None
    except OSError as exc:
        raise Fatal(f"cannot read {path}: {exc}") from exc
    bom = data.startswith(b"\xef\xbb\xbf")
    if bom:
        data = data[3:]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Fatal(f"{path} is not valid UTF-8") from None
    n_crlf = text.count("\r\n")
    n_lf = text.count("\n") - n_crlf
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return Doc(text, bom, n_crlf > n_lf)


def write_atomic(path, text, *, bom=False, crlf=False):
    """Write UTF-8 to a temp file beside path, then os.replace it into place."""
    if crlf:
        text = text.replace("\n", "\r\n")
    data = (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")
    folder = os.path.dirname(path) or "."
    try:
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".agentsmd-", suffix=".tmp")
    except OSError as exc:
        raise Fatal(f"cannot write {path}: {exc}") from exc
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except OSError as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise Fatal(f"cannot write {path}: {exc}") from exc


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(claude_text):
    """The full AGENTS.md text for a CLAUDE.md text (already LF)."""
    return HEAD3 + "<!-- source-sha256: " + sha(claude_text) + " -->\n\n" + claude_text


def parse_agents(text):
    """(header_hash, body) of a generated AGENTS.md, or None if no valid header."""
    if text is None or not text.startswith(HEAD3):
        return None
    first, _, tail = text[len(HEAD3) :].partition("\n")
    m = HASH_RE.fullmatch(first)
    if not m or not tail.startswith("\n"):
        return None
    return m.group(1), tail[1:]


def agents_rel(claude_rel):
    return claude_rel[: -len("CLAUDE.md")] + "AGENTS.md"


def is_hand_written(agents):
    """True for an AGENTS.md with content but no GENERATED header."""
    return agents is not None and agents.text.strip() != "" and not agents.text.startswith(MARKER)


def hand_written_msg(a_rel):
    return (
        f"HAND-WRITTEN {a_rel}: no GENERATED header, so it was not touched. "
        "Move its rules into CLAUDE.md, or pass --force to replace it."
    )


def sync_pair(root, claude_rel, force):
    """Two-way sync of one pair. Returns 1 on conflict or refusal, else 0."""
    c_path = os.path.join(root, *claude_rel.split("/"))
    a_rel = agents_rel(claude_rel)
    a_path = os.path.join(root, *a_rel.split("/"))
    claude = load(c_path, required=True)
    agents = load(a_path, required=False)
    if is_hand_written(agents) and not force:
        print(hand_written_msg(a_rel))
        return 1
    parsed = parse_agents(agents.text) if agents is not None else None

    def write_agents(text):
        write_atomic(a_path, text)
        print(f"wrote {a_rel}")

    if parsed is None:  # no AGENTS.md, or no valid header: generate
        write_agents(build(claude.text))
        return 0
    h, body = parsed
    c_hash, a_hash = sha(claude.text), sha(body)
    if c_hash == h and a_hash == h:
        print(f"unchanged {a_rel}")
        return 0
    if a_hash == h or body == claude.text:
        write_agents(build(claude.text))  # CLAUDE.md changed, or header stale
        return 0
    if c_hash == h:  # AGENTS.md was edited: carry the body back
        if body.strip() == "" or len(body) < MIN_BODY_RATIO * len(claude.text):
            print(
                f"REFUSED {a_rel}: body is empty or under half the size of "
                f"{claude_rel}. Nothing written."
            )
            return 1
        write_atomic(c_path, body, bom=claude.bom, crlf=claude.crlf)
        print(f"wrote {claude_rel} (from {a_rel})")
        write_agents(build(body))
        return 0
    print(f"CONFLICT {claude_rel} and {a_rel}: both changed and differ. Nothing written.")
    return 1


def run(args):
    root = os.path.abspath(args.root)
    tracked = git_ls_files(root)
    claudes = find_claude_files(tracked)
    if not claudes:
        print("agentsmd: no tracked CLAUDE.md; nothing to do.")
        return 0

    bad = 0
    for claude_rel in claudes:
        if args.sync:
            bad += sync_pair(root, claude_rel, args.force)
            continue
        c_path = os.path.join(root, *claude_rel.split("/"))
        want = build(load(c_path, required=True).text)
        a_rel = agents_rel(claude_rel)
        a_path = os.path.join(root, *a_rel.split("/"))
        agents = load(a_path, required=False)
        if agents is not None and agents.text == want:
            print(f"unchanged {a_rel}")
            continue
        if is_hand_written(agents) and not (args.force and not args.check):
            print(hand_written_msg(a_rel))
            bad += 1
            continue
        if args.check:
            state = "missing" if agents is None else "differs from CLAUDE.md"
            print(f"DRIFT {a_rel}: {state}. Fix: {FIX}")
            bad += 1
            continue
        write_atomic(a_path, want)
        print(f"wrote {a_rel}")

    if args.check:
        have_claude = {agents_rel(c) for c in claudes}
        for p in tracked:
            parts = p.split("/")
            if parts[-1] != "AGENTS.md" or p in have_claude or ".claude" in parts[:-1]:
                continue
            doc = load(os.path.join(root, *parts), required=False)
            if doc is not None and doc.text.startswith(MARKER):
                print(f"WARNING {p}: generated AGENTS.md has no CLAUDE.md beside it (orphan)")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 on drift")
    ap.add_argument(
        "--sync",
        action="store_true",
        help="two-way: carry an AGENTS.md edit back into CLAUDE.md; conflict exits 1",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="also overwrite an AGENTS.md that has no GENERATED header",
    )
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    args = ap.parse_args(argv)
    if args.check and args.sync:
        print("agentsmd: error: --check and --sync are exclusive", file=sys.stderr)
        return 2
    try:
        return run(args)
    except Fatal as exc:
        print(f"agentsmd: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
