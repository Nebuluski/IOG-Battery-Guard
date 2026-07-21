# IOG-Battery-Guard

Home Assistant automation that pauses GivEnergy battery discharge while Octopus
Intelligent Go is dispatching cheap power, then restores normal Eco when it ends.
See **[docs/setup-guide.md](docs/setup-guide.md)** for the full newbie walkthrough.

## Remit
- **Owns:** the Home Assistant automation that pauses GivEnergy battery
  discharge during Octopus Intelligent Go dispatch windows and restores Eco
  mode afterwards.
- **Does not own:** broader homelab services (Homelab-Services) or host
  provisioning (Homelab-Forge, board 20).
- **Cross-project needs:** file a card on the owning project's Vikunja board —
  never edit a sibling repo directly.

<!-- EVERGREEN:START core:setup -->
## Workflow
1. Pick a card on the board and note its task id.
2. `git switch -c task-<id>-<short-desc>` (card auto-moves to **Doing**).
3. Commit with a task ref: `feat: the thing (#<id>)` (hooks block a missing
   ref or a staged secret).
4. Push (a pre-push hook runs CI's checks locally first), open a PR, let CI
   go green, merge.
5. `git pull` on `main` (card auto-moves to **Done**).

See `CONTRIBUTING.md` for setup and the full contribution flow.
<!-- EVERGREEN:END core:setup -->
