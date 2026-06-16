# IOG-Battery-Guard

<!-- One-line description â€” edit me. This title and description are yours;
     Evergreen only manages the marked region below. -->

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
