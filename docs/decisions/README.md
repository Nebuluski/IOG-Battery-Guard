# Decision records

This folder is the project's durable record of **what was decided, when, why,
and what was rejected** — kept so the reasoning survives sessions, handoffs,
and (if it ever matters) legal challenges. Git history gives every entry a
tamper-evident timestamp and author; the project's private GitHub remote is
the off-site copy.

## Rules
- Every significant design / architecture / product decision gets a numbered
  ADR: copy `TEMPLATE.md` to `NNNN-short-slug.md` (zero-padded, next free
  number) and fill it in.
- Write it **in the same PR** as the work it explains, or at the end of the
  design session that produced it.
- Never rewrite an accepted ADR to change its meaning. If a decision changes,
  write a new ADR and mark the old one `Superseded by NNNN`.
- Interview/grilling sessions that settle multiple decisions are summarised
  into one ADR listing each question, the options considered, and the outcome.

`README.md` and `TEMPLATE.md` here are Evergreen-managed (framework); the
numbered ADRs are yours — sync never touches them.
