# Project guide for Claude Code

<!-- Anything OUTSIDE the EVERGREEN markers below is yours — project-specific
     notes, context, and overrides. Evergreen never reads or edits it. The
     marked regions are framework-owned and refreshed by `evergreen sync`. -->

<!-- EVERGREEN:START core:workflow -->
## Workflow — follow this every task
1. Start from a Vikunja card. It has **two** refs and both work everywhere:
   the scoped `CODE-nn` printed on the card itself (e.g. `NETAUD-42`) and the
   global task id (e.g. `#417`). Prefer the scoped one — it is what you can
   read straight off the board, and it cannot name another board's card.
2. Branch as `task-<ref>-<short-desc>` — `task-netaud-42-config-loader` or
   `task-417-config-loader`. The `post-checkout` hook moves the card to
   **In Progress** and attaches this repo's docs
   (README/CLAUDE.md/CONTRIBUTING/`docs\`) to the card.
3. Make small, focused commits using Conventional Commits, and **always**
   include the task ref: `feat: add config loader (NETAUD-42)`.
   The `commit-msg` hook hard-rejects a commit carrying neither form — the
   scoped one only for *this* repo's own code, read from `vikunja.config.json`.
   The `pre-commit` hook hard-rejects any commit that stages a secret (gitleaks).
4. Push the branch and open a PR. The `pre-push` hook first runs the same
   checks CI runs (ruff + pytest + Lua + Node/TS) and blocks a push that would fail.
   CI (lint + tests on Ubuntu) must be green before merge. Windows tests run
   locally via that pre-push hook, not in CI (to stay within the private-repo
   Actions minute allowance); the full CI suite is PR-only, and a push to `main`
   runs only the gitleaks secret rescan.
5. After the PR merges, `git pull` on `main` — the `post-merge` hook marks
   the card **Done**.
<!-- EVERGREEN:END core:workflow -->

<!-- EVERGREEN:START core:conventions -->
## Commit style (Conventional Commits)
`type: summary (CODE-nn)` — or `(#task)` — where type ∈ feat, fix, docs,
refactor, test, chore. `.vikunja-code` holds this repo's code so CI can check
scoped refs too; `vikunja.config.json` is gitignored, so CI can never read it.

## Code conventions
- **Python:** Ruff for lint + format, type hints, pytest. No bare `except`.
- **Lua:** Luacheck-clean, StyLua-formatted; modules return a table; no globals.
- Keep changes minimal and scoped to the task. Don't add abstractions,
  helpers, or error handling that weren't asked for.

## Hard rules
- **NEVER commit secrets.** The Vikunja token lives in `VIKUNJA_TOKEN`;
  `vikunja.config.json` and `.env` are gitignored. These repos are public.
- Don't bypass hooks (`--no-verify`) unless explicitly told to.
- `main` must stay releasable — nothing merges red.
- **Stay in your remit.** Before building any new capability, check this
  repo's `## Remit` in README.md and the workspace project registry
  ("Project registry — who owns what" in the workspace CLAUDE.md). If another
  project owns that ground, don't build it here — file a card on the owning
  project's Vikunja board
  (`python "$env:VIKUNJA_DEVKIT\vikunja-admin.py" task create <pid> "<title>" --description "<what/why + requesting repo>"`)
  and reference it. Never directly edit a sibling repo.

## Decision records (docs/decisions/)
- Every significant design/architecture/product decision gets a numbered ADR
  in `docs/decisions/` (copy `TEMPLATE.md`), committed with the work it
  explains — this is the project's durable record of what was decided, when,
  why, and what was rejected.
- Design-review or grilling sessions that settle several decisions are
  summarised into one ADR at the end of the session.
- Changed your mind? New ADR that supersedes the old one — never rewrite
  history.
<!-- EVERGREEN:END core:conventions -->

## Project-specific notes
<!-- Add anything specific to THIS project here. Safe from sync. -->

<!-- EVERGREEN:START homelab:conventions -->
## Homelab conventions
- Services sit behind a reverse proxy; route via labels/config, not ad-hoc host ports.
- YAML configs (Home Assistant, Homepage, etc.) are the source of truth — keep them
  in-repo, with secrets pulled from `.env`/`secrets.yaml` files that are gitignored.
- Validate config before reloading so a typo can't take the instance down.
- Document backup & restore for every stateful service (see `docs/homelab.md`).
- Pin image tags; update deliberately and back up before major bumps.
<!-- EVERGREEN:END homelab:conventions -->
