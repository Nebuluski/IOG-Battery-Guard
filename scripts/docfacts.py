#!/usr/bin/env python3
"""docfacts.py -- do the numbers written in the docs still match reality?

A doc can say "the stack id is 13" and drift silently the day the stack is
rebuilt. This checker never guesses at drift: it only compares a value a doc
author explicitly MARKED against a fact recorded in a small JSON file the
project maintains, `docs/facts.json` (card GEN-29, option A: explicit inline
markers -- never a heuristic scan of prose numbers).

Marker syntax (Markdown): a backtick code span immediately followed by an
HTML comment naming the fact's dotted key, with zero or one space between:

    The stack id is `13` <!--fact:vikunja.stack_id-->

The checker compares the span text, stripped, against `str(value)` for the
key `vikunja.stack_id` in the facts file. A list leaf matches if the span
text equals any one element (also compared via `str()`). Exactly this form
is recognised; a comment naming a fact with no code span directly before it
is reported as a MALFORMED marker, not silently ignored.

Facts file: a JSON object, nesting allowed, addressed by dotted path. Leaf
values are scalars (str/int/bool) or a list of scalars.

Findings, one per line, `file:line: KIND key doc='...' facts='...'`:
  MISMATCH     the marked value differs from the fact.
  UNKNOWN_KEY  the marker names a key the facts file does not have.
  MALFORMED    a `<!--fact:...-->` comment with no code span right before it.

Exit 0 with a note when the default facts file does not exist -- most repos
carry no `docs/facts.json` yet and must stay green. A missing file named
explicitly with `--facts` is an error. Otherwise: exit 1 if any finding,
else 0. Standard library only. ASCII-only output.

Usage:
  docfacts.py                      Check docs/facts.json against every *.md file.
  docfacts.py --facts PATH         Use a different facts file.
  docfacts.py --repo PATH          Operate on PATH instead of the current directory.
  docfacts.py --include-decisions  Also check docs/decisions/ (skipped by default).
  docfacts.py --exclude GLOB       Skip paths matching GLOB (repeatable).
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys

PRUNE_DIRS = {".git", ".claude", "node_modules", ".venv"}

# `` `13` <!--fact:vikunja.stack_id--> `` -- zero or one space, nothing else,
# between the closing backtick and the comment.
MARKER_RE = re.compile(r"`([^`\n]*)`[ ]?<!--fact:([A-Za-z0-9_.-]+)-->")
COMMENT_RE = re.compile(r"<!--fact:([A-Za-z0-9_.-]+)-->")


def iter_markdown_files(repo, *, include_decisions, excludes):
    """Every `*.md` under repo, skipping vendor dirs and (by default) ADRs."""
    decisions_prefix = os.path.join("docs", "decisions") + os.sep
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, repo)
            rel_posix = rel.replace(os.sep, "/")
            if not include_decisions and (
                rel == "docs/decisions" or (rel + os.sep).startswith(decisions_prefix)
            ):
                continue
            if any(fnmatch.fnmatch(rel_posix, pat) for pat in excludes):
                continue
            yield path, rel_posix


def _lookup(facts, dotted_key):
    """(found, value) for a dotted path into the facts object.

    found is False for a missing key or a path that resolves to a non-leaf
    (a dict) -- both count as UNKNOWN_KEY, since neither is a checkable fact.
    """
    node = facts
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    if isinstance(node, dict):
        return False, None
    return True, node


def _matches(doc_value, fact_value):
    if isinstance(fact_value, list):
        return any(doc_value == str(v) for v in fact_value)
    return doc_value == str(fact_value)


def _facts_repr(fact_value):
    if isinstance(fact_value, list):
        return json.dumps(fact_value)
    return str(fact_value)


def check_file(path, rel, facts):
    """(markers_checked, findings) for one Markdown file."""
    findings = []
    checked = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as e:
        return 0, [f"{rel}: could not read ({e})"]

    for lineno, line in enumerate(lines, start=1):
        valid_ends = set()
        for m in MARKER_RE.finditer(line):
            valid_ends.add(m.end())
            doc_value = m.group(1).strip()
            key = m.group(2)
            checked += 1
            found, fact_value = _lookup(facts, key)
            if not found:
                findings.append(f"{rel}:{lineno}: UNKNOWN_KEY {key} doc='{doc_value}'")
                continue
            if not _matches(doc_value, fact_value):
                findings.append(
                    f"{rel}:{lineno}: MISMATCH {key} doc='{doc_value}' "
                    f"facts='{_facts_repr(fact_value)}'"
                )
        for m in COMMENT_RE.finditer(line):
            if m.end() in valid_ends:
                continue
            findings.append(f"{rel}:{lineno}: MALFORMED {m.group(1)}")

    return checked, findings


def parse_args(argv):
    opts = {
        "repo": os.path.abspath(os.getcwd()),
        "facts": "docs/facts.json",
        "facts_given": False,
        "include_decisions": False,
        "exclude": [],
    }
    args = list(argv)
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--facts":
            opts["facts"] = args[i + 1]
            opts["facts_given"] = True
            i += 2
        elif a == "--repo":
            opts["repo"] = os.path.abspath(args[i + 1])
            i += 2
        elif a == "--include-decisions":
            opts["include_decisions"] = True
            i += 1
        elif a == "--exclude":
            opts["exclude"].append(args[i + 1])
            i += 2
        elif a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            sys.exit(f"docfacts.py: unknown argument {a!r} (try --help)")
    return opts


def main(argv):
    opts = parse_args(argv)
    repo = opts["repo"]
    if not os.path.isdir(repo):
        sys.exit(f"docfacts.py: not a directory: {repo}")

    facts_path = opts["facts"]
    if not os.path.isabs(facts_path):
        facts_path = os.path.join(repo, facts_path)

    if not os.path.isfile(facts_path):
        if opts["facts_given"]:
            print(f"docfacts.py: facts file not found: {facts_path}")
            return 1
        print(f"docfacts: no {opts['facts']}, nothing to check")
        return 0

    try:
        with open(facts_path, encoding="utf-8") as fh:
            facts = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"docfacts.py: could not read {facts_path}: {e}")
        return 1
    if not isinstance(facts, dict):
        print(f"docfacts.py: {facts_path} must be a JSON object")
        return 1

    checked = 0
    findings = []
    for path, rel in iter_markdown_files(
        repo, include_decisions=opts["include_decisions"], excludes=opts["exclude"]
    ):
        file_checked, file_findings = check_file(path, rel, facts)
        checked += file_checked
        findings.extend(file_findings)

    for line in findings:
        print(line)
    print(f"docfacts: {checked} markers checked, {len(findings)} errors")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
