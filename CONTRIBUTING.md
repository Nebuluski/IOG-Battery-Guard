# Contributing

Thanks for your interest! This project uses a lightweight, enforced workflow.

## Setup
```sh
# Python tooling
pip install ruff pytest pre-commit
pre-commit install        # runs lint/format before each commit

# Lua tooling (if working on Lua)
# luacheck + stylua must be on your PATH
```

## Making a change
1. Find or open an issue / board card and note its task ID (e.g. `#42`).
2. Branch: `git switch -c task-<id>-<short-desc>`.
3. Make small, focused commits using **Conventional Commits**, and **always
   include the task ref**:
   ```
   feat: add config loader (#42)
   fix: handle empty input (#42)
   ```
   Commits without a `#<id>` are rejected automatically.
4. Push and open a Pull Request against `main`.
5. CI (lint + tests on Windows & Ubuntu) must pass before merge.

## Definition of Done
- [ ] Tests pass locally and in CI
- [ ] Lint/format clean (Ruff / Luacheck / StyLua)
- [ ] Docs updated if behaviour changed
- [ ] The board card is moved to Done (handled automatically on merge)

## Commit types
`feat`, `fix`, `docs`, `refactor`, `test`, `chore` â€” format `type: summary (#task)`.
