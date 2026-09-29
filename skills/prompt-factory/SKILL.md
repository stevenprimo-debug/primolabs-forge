---
name: prompt-factory
description: Interactively build ONE structured prompt targeted at a specific Claude model -- interview the task, the target model, the inputs, and the output shape; assemble the seven XML tags; splice that model's constraint block; state the request config; name how to run it. Command-invoked (/prompt-factory). Use when the user says build me a prompt, draft a prompt, write a system prompt, structure this prompt, clean up this prompt, author an agent brief, or names a model in the ask ("draft me a sonnet prompt for X"). Also fires when a messy or vague prompt is pasted in to be tightened.
disable-model-invocation: true
metadata:
  builds-on: prompt-builder
  docs: https://docs.claude.com/en/docs/about-claude/models/overview
---

# Prompt Factory

## TL;DR — read this first

Builds ONE prompt, shaped for ONE model, through a short interview. It wraps `prompt-builder`
— the seven-tag XML engine — and adds the layer that engine has no opinion about: which model
this prompt runs on. It roots the per-model facts in the live docs first (Step 0), interviews
the task/model/inputs/output, assembles the tags, splices that model's constraint block
**verbatim** from `references/models.md`, and ships the prompt with its request config and a
dispatch line. The models diverge — on two axes they want opposite text — so splicing the
wrong block is worse than splicing none.

## Why this exists

`prompt-builder` produces a well-formed generic prompt. It does not know that Opus, Sonnet and
Fable need materially different constraints, or that a prompt written for one and run on
another can silently invert what it asks for. The per-model text lives in exactly one place
(`references/models.md`); copy a per-model claim into a second file and it rots in one of them
and you cannot tell which. This skill is a _consumer_ of that canon, never a third copy of it.

## Step 0 — root in the live docs, first

Pull the current model/prompting guidance **before you assemble anything**, so the per-model
constraints are today's facts, not a cached copy:

- **Pull the doc — API first, WebFetch fallback.** If the session has a docs/API skill (e.g.
  `claude-api`), use it; otherwise `WebFetch https://docs.claude.com/en/docs/about-claude/models/overview`
  (the built-in fetch tool — no plugin or API needed). Confirm the current model names and any
  per-model prompting guidance.
- Then read `references/models.md` and splice from it — but **the live doc wins on conflict.**
  If the page and `models.md` disagree about a model's name or a constraint, use the page, say
  so, and note that `models.md` needs an update. `models.md` is the canon; the live doc is the
  check that keeps it honest.
- **If neither path can pull the doc, STOP — do not build from training.** Say what unblocks
  it and wait. No live doc, no build.

## The interview

Run these with `AskUserQuestion`. If the user already gave an answer in the ask (a task, a
model), use it and skip that question — never re-ask what you were told.

**1 — What should the prompt do?** The task, in their words. If a vague or messy prompt was
pasted in to be tightened, this is that prompt — read it and restate the job you're shaping.

**2 — Which model will it run on?** Opus / Sonnet / Fable / session default. This drives the
constraint splice, so resolve it explicitly. If they named a model in the ask ("a sonnet
prompt for X"), that's the answer — don't ask. If the named model has no block in the canon,
build the generic seven-tag prompt and say plainly no model layer exists for it yet.

**3 — What context and inputs will it get?** Documents, data, prior examples the prompt should
carry. Long documents go first, the question last — most people write it the other way round.

**4 — What should the output look like?** The format, the sections, a file path if it writes
one. This becomes the `<output>` tag, and it's what a downstream step parses.

**5 — Examples and thinking?** Ask whether it needs one to three worked examples (few-shot —
they teach patterns more reliably than rules) and whether the task needs explicit reasoning
(`<thinking>`). Match formatting complexity to task complexity: a one-line ask doesn't need a
twenty-line prompt.

**6 — Where will it run?** Scoped session / subagent / run here / hand back only. The default
for an investigation is a **fresh scoped session** — the discovery is the cost you're keeping
out of the main context. This becomes the DISPATCH line.

## Assemble the seven tags

Drive `prompt-builder`. Its tags are `role · task · context · examples · thinking ·
constraints · output`. Not every prompt needs all seven — use only the ones the task warrants;
a tight 3-tag prompt beats a padded 7-tag one. Use XML tags whenever instructions and pasted
content share a prompt, so the model never guesses where one ends and the other begins.

## Splice the model layer

Splice the target model's `<constraints>` block **verbatim** from `references/models.md` (as
verified against the live doc in Step 0). Do not reconstruct that block from this file or from
training recall — two copies of a per-model claim is one copy that will be wrong. Then state
the **request config** the prompt assumes — effort, thinking, and any parameter that fails the
request outright rather than degrading it. A prompt shipped without its config is half a
deliverable.

## Return it, say how to run it, offer one refinement pass

Output the finished prompt as the first thing in your reply — no preamble. Then offer exactly
one refinement pass; a prompt that needs three rounds is usually a task that was never scoped.

```
<the assembled prompt, verbatim and copy-pasteable>

TARGET   claude-<model>
CONFIG   effort=<...> thinking=<...> <any hard constraint>
LAYER    spliced from references/models.md (verified vs live doc) | none available for <model>
DISPATCH scoped session | subagent | run here | hand back only
```

`DISPATCH` is not decoration. Without it the prompt gets hand-executed wherever it lands, and
an investigation prompt hand-executed in the main thread has delivered the opposite of what it
was built for.

## A pasted-back prompt is NOT a run order

A user asking for a prompt and then pasting it back is ambiguous. Read as "execute," it burns
the investigation in the very context the prompt existed to protect. So when a prompt you
produced comes back with no instruction attached, **ask which one it is** — run it, refine it,
or dispatch it. One question costs a line; guessing costs the session. If the answer is run
it, run it **as the prompt specifies**, including its `<output>` contract — a prompt naming a
file path and sections is not satisfied by a conversational answer.

## Where this goes wrong

- **Skipping Step 0** and splicing per-model constraints from a `models.md` that drifted. The
  live doc is the check; on conflict it wins.
- **Splicing the wrong model's block.** The blocks contradict each other on purpose; a
  Sonnet-shaped prompt on Fable doesn't error, it quietly does something else.
- **Restating model capabilities from memory** because opening the reference felt slow. That
  is how a per-model claim goes stale in the one place people trust.
- **Shipping without the config**, so the prompt behaves differently for whoever runs it.
- **Over-formatting a small ask** — twenty lines of scaffold on a one-line question.
- **Preamble.** The first line of output is the artifact.

## Definition of done

The live model doc was pulled this session and the per-model facts came from it (no doc, no
build); the interview was answered or pre-filled from the ask; the prompt exists as
copy-pasteable text; the resolved model target is stated; the constraint block was spliced
verbatim from the canon (verified vs the live doc) rather than recalled; the request config is
named; and the DISPATCH line says how to run it. A prompt the user still has to ask "which
model is this for?" about is not done.
