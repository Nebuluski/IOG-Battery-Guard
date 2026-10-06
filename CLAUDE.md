# Project guide for Claude Code

<!-- Anything OUTSIDE the EVERGREEN markers below is yours — project-specific
     notes, context, and overrides. Evergreen never reads or edits it. The
     marked regions are framework-owned and refreshed by `evergreen sync`. -->

<!-- EVERGREEN:START core:workflow -->
## Workflow — follow this every task
1. Start from a Vikunja card. Use the scoped ref on the card (`NETAUD-42`). The
   global id (`#417`) also works.
2. Branch as `task-<ref>-<short-desc>`: `task-netaud-42-config-loader`.
   `post-checkout` moves the card to **Doing**.
3. Make small commits in Conventional Commits form. **Always** include the task
   ref: `feat: add config loader (NETAUD-42)`. `commit-msg` rejects a commit
   with no ref. `pre-commit` rejects a staged secret.
4. Push and open a PR. `pre-push` runs the CI checks locally first. CI must be
   green before the merge.
5. Merge, then `git pull` on `main`. `post-merge` marks the card **Done**.
   - `(CODE-nn)` or `(#417)` closes the card.
   - **`(refs CODE-nn)` never closes it.** Use it when work remains.

## Briefing subagents
Give every subagent:
- one absolute snapshot path, outside any git worktree;
- the `.env` path, never a credential hunt;
- a hard tool-call limit, with "report what you have";
- a text-only report: no commit, PR or findings doc.

The main thread writes one combined PR at the end.
<!-- EVERGREEN:END core:workflow -->

<!-- EVERGREEN:START core:conventions -->
## Commit style (Conventional Commits)
`type: summary (CODE-nn)`, where type is feat, fix, docs, refactor, test or
chore.
- Put the ref in a bracket that holds nothing but refs. A number in prose
  (`monitor #48`) closes nothing.
- `.vikunja-code` holds this repo's code for CI. Keep it tracked.

## Code conventions
- **Python:** Ruff for lint + format, type hints, pytest. No bare `except`.
- **Lua:** Luacheck-clean, StyLua-formatted; modules return a table; no globals.
- Keep changes minimal and scoped to the task. Add no abstraction, helper or
  error handling that the task did not ask for.

## Hard rules
- **NEVER commit secrets.** The Vikunja token lives in `VIKUNJA_TOKEN`.
  `vikunja.config.json` and `.env` are gitignored. Treat every repo as public.
- Never bypass hooks (`--no-verify`) unless explicitly told to.
- `main` must stay releasable. Nothing merges red.
- **Stay in your remit.** Before you build a new capability, check this repo's
  `## Remit` in README.md and the project registry in the workspace CLAUDE.md.
  If another project owns that ground, file a card on its board:
  `python "$env:VIKUNJA_DEVKIT\vikunja-admin.py" task create <pid> "<title>" --description "<what/why + requesting repo>"`.
  Never edit a sibling repo directly.
- **Rules only in this file.** Never add a reason, a date, an owner quote or an
  incident. Put those in `docs/`.

## Decision records (docs/decisions/)
- Every significant design, architecture or product decision gets a numbered
  ADR in `docs/decisions/` (copy `TEMPLATE.md`). Commit it with the work.
- Summarise a design-review or grilling session into one ADR at its end.
- Changed your mind? Write a new ADR that supersedes the old one. Never rewrite
  an old ADR.
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
