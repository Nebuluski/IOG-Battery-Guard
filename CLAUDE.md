# Project guide for Claude Code

<!-- Anything OUTSIDE the EVERGREEN markers below is yours — project-specific
     notes, context, and overrides. Evergreen never reads or edits it. The
     marked regions are framework-owned and refreshed by `evergreen sync`. -->

<!-- EVERGREEN:START core:workflow -->
## Workflow — follow this every task
1. Start from a Vikunja card; note its task ID (e.g. `#42`).
2. Branch as `task-<id>-<short-desc>` (e.g. `task-42-config-loader`).
   The `post-checkout` hook moves the card to **In Progress**.
3. Make small, focused commits using Conventional Commits, and **always**
   include the task ref: `feat: add config loader (#42)`.
   The `commit-msg` hook hard-rejects any commit without `#<id>`; the
   `pre-commit` hook hard-rejects any commit that stages a secret (gitleaks).
4. Push the branch and open a PR. The `pre-push` hook first runs the same
   checks CI runs (ruff + pytest + Lua) and blocks a push that would fail.
   CI (lint + tests on Windows & Ubuntu) must be green before merge.
5. After the PR merges, `git pull` on `main` — the `post-merge` hook marks
   the card **Done**.
<!-- EVERGREEN:END core:workflow -->

<!-- EVERGREEN:START core:conventions -->
## Commit style (Conventional Commits)
`type: summary (#task)` where type ∈ feat, fix, docs, refactor, test, chore.

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
