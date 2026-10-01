---
name: recall
description: >-
  Carry working context across Cowork sessions through a plain RECALL.md file in the
  project's folder -- Cowork keeps project memory but exposes no way for a skill to read or
  write it, so this skill owns a file you can see and edit. Fire when the user says "recall",
  "catch me up", "where did we leave off", "what did we do last time", "what's the status",
  "remember this for next time", "save this to recall", "log this", "update the recall",
  "note this for later", or at the start of a work session when continuity would help. Two
  moves: READ (summarize the latest RECALL.md entries to restore context) and SAVE (append a
  dated, structured entry). Pure file I/O -- no database, no network, no graph. Works in any
  Cowork project that has an attached folder.
license: MIT
metadata:
  version: "1.0.0"
  author: PrimoLabs
---

# Recall — cross-session memory on a file you can see

Cowork persists project memory across sessions, but **no skill-facing API exists to read or
write that store**, and Cowork does not read Claude Code's `~/.claude` directory. The
dependable, portable substrate is a plain file in the project's attached folder. This skill
owns one file — `RECALL.md` — and does exactly two things with it.

The file lives at the **root of the project's first attached folder** (where files Claude
creates in Cowork land). Find it with Glob (`**/RECALL.md`, shallowest match) or look in the
current working directory. If none exists, SAVE creates it there.

## READ — restore context (triggers: "recall", "catch me up", "where did we leave off")

1. Locate `RECALL.md`. If none exists, say so plainly ("no recall log yet in this project")
   and stop — do not invent history.
2. Read it. Summarize the **most recent 1–3 entries** first (reverse-chronological), leading
   with: what was last done, decisions made, what is still open, and the stated next step.
3. Keep it tight — a few lines, not the whole file. Offer to show older entries if asked.

Never state as fact anything not in the file. The log is the record; if it is silent on
something, say it is silent.

## SAVE — append an entry (triggers: "save to recall", "log this", "remember this for next time")

Append a new entry to the **top** of the entries section (newest first), in this fixed shape
so every entry reads the same and READ can parse them:

```markdown
## 2026-10-01 — <short session label>

**Did:** <1–3 bullets of what happened>
**Decisions:** <decisions made, or "none">
**Open:** <unresolved questions / blockers, or "none">
**Next:** <the single next action>
```

Rules:
- Use today's real date (`YYYY-MM-DD`). Never guess a date.
- **Append, never overwrite.** A recall log is a record; earlier entries are never rewritten
  or deleted. If the file does not exist, create it with the header below, then the entry.
- Keep each entry short — this is a memory jog, not a transcript. One screenful at most.
- Capture only what a future session needs to continue: outcomes, decisions, open loops, next
  step. Leave out blow-by-blow detail.

New-file header (write once, above the entries):

```markdown
# Recall Log

Cross-session memory for this project, maintained by the `recall` skill. Newest entry first.
```

## Scope

- Pure local file I/O; no network, no database, no credentials.
- One file per project (`RECALL.md` at the project folder root). Do not scatter copies.
- This is a convenience log the model maintains — it is not Cowork's native project memory
  (which the app manages on its own and this skill does not touch).
