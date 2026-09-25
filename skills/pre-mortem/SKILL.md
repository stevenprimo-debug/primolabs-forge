---
name: pre-mortem
description: >-
  Pre-mortem failure-mode surfacing. Imagine the plan already FAILED 6 months out -- work backward through what killed it. Gary Klein technique (HBR, "Performing a Project Premortem", Sep 2007). Use BEFORE big builds, before product launches, before architecture lock, before campaign launches. Use when: "pre-mortem", "stress-test this plan", "what could break this", "before we commit", "is this plan brittle", "failure-mode review", "what would kill this".
metadata:
  when_to_use: |
    - Before any plan >= 1 week of work -- pre-mortem surfaces ~30% more failure modes than standard risk review
    - Before architecture lock -- find the brittle assumptions before they ship
    - Before product launch -- surface the hidden "this only works if X" dependencies
    - Before a big campaign launch -- what makes this go to zero?
    - Distinct from demand validation. Pre-mortem validates DURABILITY.
  when_not_to_use: |
    - Already-shipping work (use /investigate for root-cause on real failures)
    - Brainstorming new ideas (use product-brainstorming or office-hours)
    - Small reversible calls (this is for >= 1 week of work or irreversible commits)
  inputs:
    - plan (required): the plan to stress-test (path to plan doc, or pasted summary)
    - >-
      horizon (optional): "3mo" | "6mo" | "12mo" -- default 6mo (the imagined-failure timeline)
    - >-
      facilitator_mode (optional): "solo" (single agent imagines + lists) | "panel" (dispatch 3-5 subagents from different lenses)
  outputs:
    - failure_modes.md: ranked list of failure modes with likelihood + severity + leading indicator
    - >-
      mitigation_plan.md: top 5 mitigations + decision: ship / revise / kill
---

# pre-mortem — Failure-Mode Surfacing

## The Klein protocol (adapted)

**Premise:** the plan has already failed. It's 6 months from now. The launch was a disaster. You are at the post-mortem meeting. **Why did it fail?**

Asking "why DID it fail" (past tense, certain) surfaces ~30% more failure modes than "what COULD go wrong" (future tense, hypothetical). The brain treats the imagined past as known and works backward through causal chains.

## Step 0 — Load the plan

Read the plan doc. If pasted summary, normalize to a 1-page brief with: goal, scope, timeline, key dependencies, success criteria.

## Step 1 — Imagine the failure

State explicitly: "It is now {today + horizon}. The plan failed. We are doing the post-mortem."

Generate 3 distinct failure scenarios:

- **Soft fail:** shipped but didn't move the metric
- **Hard fail:** didn't ship by the deadline
- **Catastrophic fail:** shipped, broke something else, net-negative

## Step 2 — List failure modes (10-20 minimum)

For each scenario, work backward. What chain of events led here? Be specific. "Adoption was low" is not a failure mode — "we built a feature that solved a problem nobody actually had because we never tested the assumption with 5 prospects" is.

**Forcing prompts:**

- What did we assume that turned out to be false?
- Who didn't show up that we counted on?
- What dependency broke that we had no fallback for?
- What competitor move did we not anticipate?
- What internal capacity bottleneck did we ignore?
- What edge case turned out to be the median case?
- What did our champion do (leave / lose budget / change roles)?
- What got de-prioritized when something urgent came up?

## Step 3 — Score each failure mode

| Failure mode | Likelihood (1-5) | Severity (1-5) | Score | Leading indicator                                                 |
| ------------ | ---------------- | -------------- | ----- | ----------------------------------------------------------------- |
| {mode}       | {L}              | {S}            | {L×S} | {observable signal that says "this is happening to us right now"} |

Rank by score. Top 5 = the load-bearing failure modes.

## Step 4 — Mitigation per top-5

For each of the top 5:

- **Mitigate** — concrete change to the plan that reduces likelihood or severity
- **Detect** — what to watch for that signals this is starting
- **Bail** — at what threshold do we kill the plan vs continue

## Step 5 — Verdict

- 🟢 **Ship** — top failure modes are mitigated to acceptable residual risk; leading indicators wired
- 🟡 **Revise** — plan needs N changes before ship; revised plan re-runs pre-mortem
- 🔴 **Kill** — top failure mode has no acceptable mitigation; do not commit

## Panel mode (optional)

For high-stakes plans, dispatch 3-5 subagents from different lenses to surface failure modes:

- **The customer** — what customer behavior kills this?
- **The competitor** — what competitor move kills this?
- **The team** — what internal capacity / morale / departure kills this?
- **The market** — what macro shift kills this?
- **The tech** — what dependency / scaling / security failure kills this?

Each subagent generates 5-10 failure modes in their lens. Main thread synthesizes + de-duplicates + ranks.

## Output

Two files in the working directory:

- `premortem_failure_modes_{date}.md` — full failure-mode list with scores
- `premortem_mitigation_plan_{date}.md` — top-5 mitigations + verdict

Chat-surface return: 1-paragraph verdict (ship/revise/kill) + top-3 failure modes + path to full docs.

## Cross-references

- Pairs with `office-hours` (demand validation) → pre-mortem (durability validation) → autoplan (build planning)
- Pairs with `architecture` skill (lock infra before code) — run pre-mortem on the architecture before locking
- Distinct from `risk-assessment` (operations skill; ongoing risk register) — pre-mortem is one-shot pre-commit

## Source

Gary Klein. "Performing a Project Premortem." Harvard Business Review, September 2007. Adapted for AI agent execution.
