# Homelab notes

## Reverse proxy
Expose services through the reverse proxy via labels/config rather than raw host
ports where possible. Keep one source of truth for routes. Trust proxy headers
only from the proxy's network, never from the public edge.

## Configuration as data
Home Assistant, Homepage, and similar tools are driven by YAML config. Keep that
config in-repo so it is versioned and reviewable. Pull secrets from `.env` or a
`secrets.yaml` that is gitignored — never inline tokens. Validate config before
reloading (e.g. `ha core check`) so a typo doesn't take the instance down.

## Backup & restore
For every stateful service, document:
- **What** to back up (named volumes, config dirs, databases, `.storage/`).
- **How** to restore from a clean host, step by step.
- **Cadence** — automate it; a manual backup is one you'll forget.

Test the restore at least once — an untested backup is a guess.

## Updates
Pin image tags and update deliberately. Read release notes for breaking changes
(especially Home Assistant, which deprecates aggressively). Snapshot/back up
before any major version bump so rollback is one step.
