---
name: skill-factory
description: Author one skill at .claude/skills/<name>/SKILL.md -- write the triggering description, structure the body against Anthropic's skill-creator standard, split detail into references, add evals when the output is checkable, validate. Use whenever the user says build a skill, make a skill, author a skill, new skill, turn this into a skill, or skillify this. Also fires when a workflow has been done twice by hand and should stop being re-derived.
disable-model-invocation: true
metadata:
  docs: https://code.claude.com/docs/en/skills
---

# Skill Factory

Builds ONE skill. A skill is a folder — `.claude/skills/<name>/SKILL.md` plus optional
siblings — that loads into the _main_ conversation when its description matches. It sees
what was just said and can ask a question mid-task, which is exactly what a subagent cannot.

Reach for a skill when the work is interactive, needs conversation context, needs many
tools, or is a workflow you keep re-deriving. Reach for `agent-factory` instead when the
work wants isolation — a fresh reviewer, a parallel sweep, a verdict returned blind.

## Ground truth is Anthropic's live skills doc

The frontmatter schema, description-cap, `metadata:` policy, and load semantics below track
https://code.claude.com/docs/en/skills. Anthropic's own upload check rejects unknown
frontmatter keys with a hard error, and the description+`when_to_use` text is truncated at
1,536 characters in the skill listing — both stated by the live doc, not derivable. Before
asserting that a field is allowed, or that a behavior applies, fetch the doc. When a claim
comes from training rather than the page you read this session, say **"From training, not a
doc:"** so the user can check it. `docs:` on a skill lives under `metadata:`; the same
doc names `metadata` as the sanctioned free-form map and warns off reusing spec field names
as keys.

## The description is the product

It is the only part always in context, and it alone decides whether the skill ever fires.
Claude **under**-triggers, so write it pushy: say what the skill does _and_ name the
contexts and phrasings that should invoke it, including ones where the user never says
the skill's name.

Weak — a topic:

> Author a case study.

Strong — a router rule:

> Author a client case study end-to-end: gather sourced facts, draft, render, hold for
> sign-off. Use whenever the user mentions a case study, a proof asset, a client success
> story, or wants to show a prospect what an engagement produced — even without the words
> "case study."

If you cannot name three phrasings that should fire it, the skill is not scoped yet.

## Two modes

**author** — a new skill from nothing. Most invocations.

**rebuild** — absorb or deepen an existing skill. The moment there is a source file, the
source-preservation contract below is armed and the verify gate is not optional.

## Emit the scaffold

```
py -3 ${CLAUDE_PLUGIN_ROOT}/scripts/factory.py skill <slug> --desc "<the router-rule description>" [--docs <url>]
```

`--docs` is required once the body names a third-party service: declare the canonical URL
and fetch it when needed rather than trusting recall. Vendors move faster than any cached
copy of their docs, and a wrong API version usually fails _forward_ — it behaves differently
instead of erroring, which is far harder to notice.

## Structure the body

Fill every `{{...}}` slot. The shape comes from `templates/skill.md`:

- **What it does and why** — one paragraph. Explain the reasoning behind the approach, not
  just the steps. A model that understands why can handle the case you did not anticipate.
- **Workflow** — imperative, numbered. Where a step could plausibly be done another way, say
  why it is done this way.
- **Output format** — show the literal shape, not a description of it. This is the one place
  a rigid template is right, because something downstream parses it.
- **Examples** — one to three, concrete in and concrete out. Examples teach patterns more
  reliably than rules and are cheaper to get right.
- **Where this goes wrong** — name the failure and its _mechanism_. "Numbers get quoted
  without their source because the source felt obvious while drafting" beats "NEVER quote an
  unsourced number." A stated mechanism survives paraphrase; a bare prohibition gets
  rationalised around.

Do not write blocks of capitalised ALWAYS/NEVER. Anthropic's own skill-creator names that a
yellow flag and asks for reasons instead.

## Keep the body small; push detail down

Three loading levels, and the cost differs by an order of magnitude at each:

| Level                                  | Loads                | Budget          |
| -------------------------------------- | -------------------- | --------------- |
| name + description                     | always               | keep it tight   |
| SKILL.md body                          | when the skill fires | under 500 lines |
| `references/` · `scripts/` · `assets/` | only when pointed at | unbounded       |

An invoked skill's body stays in context for the session, so a bloated SKILL.md is a
permanent per-session cost. Push long material into `references/`, executable work into
`scripts/` (executed, never loaded), and output templates into `assets/`.

**Never name a sibling that does not exist.** A pointer to a missing file is worse than no
pointer — it promises depth that is not there and nothing errors.

## Add evals when the output is checkable

If the skill produces something objectively verifiable — a file transform, an extraction, a
fixed verdict — write two or three realistic test prompts to `evals/evals.json` and run them
before calling it done:

```json
{
  "skill_name": "<slug>",
  "evals": [
    {
      "id": 1,
      "prompt": "the kind of thing a user would actually type",
      "expected_output": "what a correct run produces",
      "files": []
    }
  ]
}
```

Skills whose output is a judgment call — voice, design, tone — are reviewed by eye instead.
Do not force assertions onto work that needs taste.

## Rebuilding: the source-preservation contract

When you are absorbing an existing skill, **every section of the source has to survive** —
its procedures, tables, formulas and worked examples come across. Cutting the prose around
them is expected; losing one of them is the failure.

Enumerate the source's sections first, so you know what you are on the hook for:

```
py -3 ${CLAUDE_PLUGIN_ROOT}/scripts/skill_factory.py headers --file <source>
```

Author with every source section's content carried across, then gate it before writing:

```
py -3 ${CLAUDE_PLUGIN_ROOT}/scripts/skill_factory.py verify --source <source> --output <draft>
```

**One gate: header survival.** Every source header must survive as a real **header** in the
output — not as a substring of prose, so a casual mention of "setup" cannot count as a
preserved `## Setup`. Matches are occurrence-counted, so collapsing two sections under one
shared heading is caught as a drop.

An empty source, or one with zero real headers, is itself a FAIL — there is nothing to
preserve, so a green verdict would be meaningless.

Size is reported and **not gated**. A length gate would fail the work this repo exists to
do: the rebuilds that matter usually get shorter, because most of what a legacy file carries
is superseded rulings, changelogs and dead pointers. Length cannot tell "I cut 15KB of
history" from "I threw away the procedure." Header survival can — which is why it is the
only gate left.

**Exit 1 means halt.** Read the `DROPPED:` list, restore those sections, re-run. Never write
a draft that failed the gate.

The failure this exists to prevent is specific and it happened: a 351-line source rebuilt as
a 145-line shell that kept **1 of 26** section headers. It looked like a clean, well-organised
skill. It had thrown away the content and kept the shape.

**Paraphrasing is dropping.** Procedures, tables, formulas and worked examples come across
verbatim. The house layer goes _on top of_ source content, never _instead of_ it.

## Validate

```
py -3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py
```

Checks the load path, body size, description presence, official frontmatter fields, declared
vendor docs under `metadata:`, undeclared network calls in bundled scripts, and the scrap
detector. CLEAN before it counts as built.

## Confirm it loaded — structure is not reachability

`validate.py` checks the shape of the file. It cannot check that Claude Code found it. Those
are different questions. A skill can be perfectly well-formed and still sit at a path Claude
Code never scans — it passes every structural check, and it is invisible anyway, with nothing
to tell you.

So the last step is observation, not inspection:

- **A skill** appears in the invocable listing by name as soon as it is written. Look for it.
- **An agent** appears in the available agent types.

If it does not appear, the file is on disk and dead — check the path before touching the
content. A malformed skill at the right path is fixable; a perfect one at the wrong path is
invisible, and nothing errors to tell you.

## Where this goes wrong

- **Writing a skill that should have been an agent.** If the work wants a cold second opinion
  or runs in parallel, the main conversation is the wrong place for it.
- **A description that names a topic instead of trigger cases.** The skill then exists and
  never fires, which looks identical to not having built it.
- **Detail left in SKILL.md because splitting felt premature.** It is a per-session cost from
  the first invocation, not a future one.
- **Prohibitions with no stated reason.** They get followed until they are inconvenient.
- **Naming `references/` and `evals/` in the body without creating them.** Aspirational
  structure reads as real structure to the next session.

## Definition of done

The folder exists at `.claude/skills/<slug>/`, the description names concrete trigger cases,
every `{{...}}` slot is filled, the body is under 500 lines with detail pushed into siblings
that actually exist, evals are written if the output is checkable, `validate.py` is CLEAN,
and the skill appears in the invocable listing — observed, not assumed.
