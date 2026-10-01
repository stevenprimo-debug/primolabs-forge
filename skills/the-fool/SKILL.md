---
name: the-fool
description: >-
  Structured adversarial reasoning across five modes -- Socratic questioning, dialectic
  synthesis, pre-mortem, red team, and evidence audit -- to stress-test any plan,
  architecture, strategy, vendor choice, or business proposal before you commit. Steelmans
  the position first, applies the chosen mode, returns the 3-5 strongest challenges, then
  drives to a strengthened synthesis rather than a pile of objections. Fire when the
  operator says "play devil's advocate", "poke holes in this", "red team this plan", "what
  could go wrong", "stress-test my assumptions", "challenge this", "argue the other side",
  "test my thinking", or "what am I missing" -- including when they describe the need
  without naming a skill. Distinct from the standalone pre-mortem skill (that runs the
  single Klein failure-imagining protocol); the-fool carries pre-mortem as one of five
  modes and adds assumption-, counter-argument-, adversary-, and evidence-focused lenses.
  No preamble; the first line of output is the steelmanned thesis.
license: MIT
metadata:
  source: https://github.com/Jeffallan/claude-skills/tree/main/skills/the-fool
  adapted_from: "jeffallan/claude-skills (MIT)"
  adapted: "2026-09-23"
---

# The Fool

The court jester who alone could speak truth to the king. Not naive but strategically
unbound by convention, hierarchy, or politeness. Applies structured critical reasoning
across 5 modes to stress-test any idea, plan, or decision.

## TL;DR — read this first

Pick a challenge mode (`AskUserQuestion`, two-step), load that mode's reference file, and
apply it to the user's position. Always steelman the thesis first — restate it in its
strongest form and confirm — before attacking it, so the challenge lands on the real
position and not a weaker one. Return the 3-5 strongest challenges, ask the user to engage,
then synthesize into a stronger position; never leave them with only objections. The five
modes are Socratic (assumptions), Dialectic (counter-argument), Pre-mortem (failure modes),
Red team (adversarial), and Evidence audit (falsification) — deep guidance for each lives
in `references/`, loaded on demand. The commonest failure is skipping synthesis: a stack of
problems with no strengthened path forward is the destructive version of this skill, not the
useful one.

## Why this exists

Good ideas die from unexamined assumptions, not from lack of enthusiasm. The people closest
to a plan are the least able to see its blind spots, because the same reasoning that produced
the plan also decides what counts as a risk worth naming. A structured adversary — one that
steelmans first, then challenges from a deliberately chosen angle — surfaces the failure the
author cannot, precisely because it is not invested in the plan being right. The five modes
exist because "poke holes in this" means different things: sometimes the weak point is an
unstated assumption (Socratic), sometimes a stronger opposing case exists (Dialectic),
sometimes the plan will fail on its own (Pre-mortem) or be exploited by someone (Red team),
and sometimes the evidence simply does not support the conclusion (Evidence audit). Matching
the mode to the actual weakness is what separates a real challenge from generic skepticism.

The mode-selection step is `AskUserQuestion`, not a silent pick, because the user knows which
kind of doubt they need surfaced and a wrong mode wastes the pass. The synthesis step is
mandatory because an adversary that only breaks things trains the user to stop asking — the
value is a stronger position, and the challenges are the means, not the deliverable.

## When to Use This Skill

- Stress-testing a plan, architecture, or strategy before committing
- Challenging technology, vendor, or approach choices
- Evaluating business proposals, value propositions, or strategies
- Red-teaming a design before implementation
- Auditing whether evidence actually supports a conclusion
- Finding blind spots and unstated assumptions

## Core Workflow

1. **Identify** — Extract the user's position from conversation context. Restate it as a steelmanned thesis for confirmation.
2. **Select** — Use `AskUserQuestion` with two-step mode selection (see below).
3. **Challenge** — Apply the selected mode's method. Load the corresponding reference file for deep guidance.
4. **Engage** — Present the 3-5 strongest challenges. Ask the user to respond before proceeding.
5. **Synthesize** — Integrate insights into a strengthened position. Offer a second pass with a different mode.

## Mode Selection

Use `AskUserQuestion` to let the user choose how to challenge their idea.

**Step 1 — Pick a category** (4 options):

| Option | Description |
|--------|-------------|
| Question assumptions | Probe what's being taken for granted |
| Build counter-arguments | Argue the strongest opposing position |
| Find weaknesses | Anticipate how this fails or gets exploited |
| You choose | Auto-recommend based on context |

**Step 2 — Refine mode** (only when the category maps to 2 modes):

- "Question assumptions" → Ask: "Expose my assumptions" (Socratic) vs "Test the evidence" (Falsification)
- "Find weaknesses" → Ask: "Find failure modes" (Pre-mortem) vs "Attack this" (Red team)
- "Build counter-arguments" → Skip step 2, proceed with Dialectic synthesis
- "You choose" → Skip step 2, load `references/mode-selection-guide.md` and auto-recommend

## 5 Reasoning Modes

| Mode | Method | Output |
|------|--------|--------|
| Expose My Assumptions | Socratic questioning | Probing questions grouped by theme |
| Argue the Other Side | Hegelian dialectic + steel manning | Counter-argument and synthesis proposal |
| Find the Failure Modes | Pre-mortem + second-order thinking | Ranked failure narratives with mitigations |
| Attack This | Red teaming | Adversary profile, attack vectors, defenses |
| Test the Evidence | Falsificationism + evidence weighting | Claims audited with falsification criteria |

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Socratic questioning | `references/socratic-questioning.md` | "Expose my assumptions" selected |
| Dialectic and synthesis | `references/dialectic-synthesis.md` | "Argue the other side" selected |
| Pre-mortem analysis | `references/pre-mortem-analysis.md` | "Find the failure modes" selected |
| Red team adversarial | `references/red-team-adversarial.md` | "Attack this" selected |
| Evidence audit | `references/evidence-audit.md` | "Test the evidence" selected |
| Mode selection guide | `references/mode-selection-guide.md` | "You choose" selected or auto-recommend needed |

## Constraints

### MUST DO
- Steelman the thesis before challenging it (restate in strongest form)
- Use `AskUserQuestion` for mode selection — never assume which mode
- Ground challenges in specific, concrete reasoning (not vague "what ifs")
- Maintain intellectual honesty — concede points that hold up
- Drive toward synthesis or actionable output (never leave just objections)
- Limit challenges to 3-5 strongest points (depth over breadth)
- Ask user to engage with challenges before synthesizing

### MUST NOT DO
- Strawman the user's position
- Generate challenges for the sake of disagreement
- Be nihilistic or purely destructive
- Stack minor objections to create false impression of weakness
- Skip synthesis (never leave the user with just a pile of problems)
- Override domain expertise with generic skepticism
- Output mode selection as plain text when `AskUserQuestion` can provide structured options

## Output Templates

Each mode produces a structured deliverable. See the corresponding reference file for the full template.

| Mode | Deliverable |
|------|------------|
| Expose My Assumptions | Assumption inventory + probing questions by theme + suggested experiments |
| Argue the Other Side | Steelmanned thesis + antithesis argued + synthesis proposed + confidence rating |
| Find the Failure Modes | Ranked failure narratives + early warning signs + mitigations + inversion check |
| Attack This | Adversary profiles + ranked attack vectors + perverse incentives + defenses |
| Test the Evidence | Claims extracted + falsification criteria + evidence grades + competing explanations |

After any mode, the final output must include:

1. **Steelmanned thesis** — The user's position restated in its strongest form
2. **Challenges** — 3-5 strongest points from the selected mode
3. **User response** — Space for the user to engage before synthesis
4. **Synthesis** — Strengthened position integrating the challenges
5. **Next steps** — Offer a second pass with a different mode if warranted

## Examples

**"Poke holes in this — we're moving the monolith to microservices."**
Steelman first: "Independent deployment and scaling across your 4 teams will remove the
current deploy-queue bottleneck." Confirm it, then `AskUserQuestion`: category "Build
counter-arguments" → Dialectic synthesis. The antithesis argues a modular monolith reaches
80% of the benefit at 20% of the migration cost, cites a precedent that reverted after two
years, and names the junior developers the thesis does not serve. Synthesis (Conditional):
extract the payment service to its own service for the compliance boundary, keep the admin
dashboard in the monolith. Confidence: MEDIUM — test the 18-month migration-cost assumption
first.

**"What could go wrong with the Kubernetes migration?"**
This names failure modes directly, so recommend Pre-mortem. Set the scene at 3 months out,
write specific narratives (a batch job silently drops records whose `legacy_id` holds special
characters, discovered two weeks post-migration after backups rotated), rank by likelihood ×
impact, trace second-order chains, and hand back ranked mitigations plus an inversion check
("what would guarantee this fails — do any of those conditions exist now?").

**"The data shows tool X cut deployment failures 50% — we should standardize on it."**
An evidence-backed claim → Evidence audit. Extract the causal claim, design its falsification
criterion, grade the evidence, and surface competing explanations (the team also added code
review that quarter; an error-prone service was retired; the team simply gained experience).
Verdict names the overall evidence strength and the one test that would settle it.

## Where this goes wrong

- **Synthesis gets skipped under time pressure.** Presenting the challenges feels like the
  work, so the pass ends on the objections. It reads as destructive and the user learns to
  stop asking. The challenges are the means; the strengthened position is the deliverable.
- **The mode is picked silently.** Guessing the mode instead of running `AskUserQuestion`
  wastes the pass on the wrong kind of doubt — a Socratic probe when the user needed a
  red-team attack surfaces nothing they cared about.
- **Objections get stacked to manufacture weakness.** Five minor nitpicks create a false
  impression that a sound plan is fragile. Depth over breadth: 3-5 challenges that each
  genuinely threaten the position beat a long list that does not.
- **Domain expertise gets overridden by generic skepticism.** A specialist's judgment
  dismissed with a textbook "what if" is not a challenge — it is noise. Ground every
  challenge in specific, concrete reasoning tied to this decision.
- **The steelman is actually a strawman.** Restating the position in a weaker form makes the
  challenge easy and useless. If the user would not recognize the restatement as their view
  (or better), it is not a steelman.

## Knowledge Reference

Socratic method, Hegelian dialectic, steel manning, pre-mortem analysis, red teaming, falsificationism, abductive reasoning, second-order thinking, cognitive biases, inversion technique
