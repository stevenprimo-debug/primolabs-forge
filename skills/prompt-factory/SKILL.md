---
name: prompt-factory
description: Build one structured, shippable prompt targeted at a specific Claude model -- assemble the seven XML tags, splice that model's constraint block, and state the request config it assumes. Use when the user says build me a prompt, draft a prompt, write a system prompt, structure this prompt, clean up this prompt, author an agent brief, or names a model in the ask ("draft me a sonnet prompt for X", "opus prompt for Y"). Also fires when a messy or vague prompt is pasted in to be tightened.
disable-model-invocation: true
metadata:
  builds-on: prompt-builder
  docs: https://docs.claude.com/en/docs/about-claude/models/overview
---

# Prompt Factory

## TL;DR — read this first

Builds ONE prompt, shaped for ONE model. It wraps `prompt-builder` — the seven-tag XML engine
— and adds the layer that engine has no opinion about: which model this prompt is going to
run on. Resolve the target from the ask, assemble the tags, then splice that model's
constraint block **verbatim** from `references/models.md`. The models diverge, and on two
axes they want opposite text, so splicing the wrong block is worse than splicing none. Ship
the prompt with its request config or it is half a deliverable.

## Why this exists

`prompt-builder` produces a well-formed generic prompt. It does not know that Opus, Sonnet and
Fable need materially different constraints, or that a prompt written for one and run on
another can silently invert what it asks for.

The reason this is a skill rather than a habit: the per-model text lives in exactly one place.
Copy a per-model claim into a second file and it rots in one of them, and you cannot tell
which. This skill is a _consumer_ of the model canon, never a third copy of it.

## Step 1 — Resolve the model target

A prompt is shaped for a model, not just a task. Read the target out of the ask before
assembling anything:

| User says                                          | Target              |
| -------------------------------------------------- | ------------------- |
| "draft me a **sonnet** prompt to X"                | `claude-sonnet-5`   |
| "draft me a **fable** prompt to X"                 | `claude-fable-5`    |
| "draft me an **opus** prompt to X"                 | `claude-opus-5`     |
| names a model mid-sentence — "…run this on sonnet" | that model          |
| no model named                                     | the session default |

The name can appear anywhere in the request. Resolve it, and state which target you shaped
for in the closing line — never silently assume, and never ask which model when one was
already named.

If the ask names a model with no block in the canon, build the generic seven-tag prompt and
say plainly that no model layer exists for it yet. Inventing one from recall is the failure
this whole skill is built to avoid.

## Step 2 — Assemble the seven tags

Drive `prompt-builder`. Its tags are `role · task · context · examples · thinking ·
constraints · output`. Not every prompt needs all seven — knowing the full set is what lets
you diagnose why a prompt is underperforming.

Two ordering rules worth applying while assembling:

- **Long documents first, the question last.** Most people write it the other way round.
- **XML tags whenever instructions and pasted content share a prompt**, so the model is never
  guessing where one ends and the other begins.

Match formatting complexity to task complexity. A one-sentence ask does not need a twenty-line
prompt, and padding one is a cost with no return.

## Step 3 — Splice the model layer

Read `references/models.md` and splice the target model's `<constraints>` block **verbatim**.

Do not reconstruct that block from this file, and do not answer model-capability questions
from training recall. That file is the canon and it is kept current against the official docs;
this file deliberately does not restate its contents, because two copies of a per-model claim
is one copy that will be wrong.

Then state the **request config** the prompt assumes — effort, thinking, and any parameter
that fails the request outright rather than degrading it. Each model's config paragraph
carries them. A prompt shipped without its config is half a deliverable.

## Step 4 — Return it, say how to run it, offer one refinement pass

Output the finished prompt as the first thing in your reply — no preamble, no "here's what I
built." Then offer exactly one refinement pass. One, because a prompt that needs three rounds
is usually a task that was never scoped, and more rounds hide that rather than fix it.

**Name the dispatch.** A prompt that does not say how it should be run gets hand-executed in
the main thread, which throws away the reason it was written. State it in the DISPATCH line of
the return: a fresh session, a subagent, another tool, or right here.

The default for an investigation is a **scoped session**, because the discovery is the cost you
are trying to keep out of the main context. A prompt whose whole value is "do the digging
elsewhere and hand back a report" is worth nothing if the digging happens in this window.

## A pasted-back prompt is NOT a run order

A user asking for a prompt and then pasting it back is ambiguous, and it has already
been resolved the expensive way: the session read the paste as "execute," improvised in the
main thread, produced none of the seven output sections the prompt specified, and burned the
investigation in the context the prompt existed to protect.

So when a prompt you produced comes back with no instruction attached, **ask which one it is** —
run it, refine it, or dispatch it. One question costs a line. Guessing costs the session.

If the answer is run it, run it **as the prompt specifies** — including its output contract.
A prompt with an `<output>` section naming a file path and named sections is not satisfied by
a conversational answer that covers the same ground.

## What this returns

```
<the assembled prompt, verbatim and copy-pasteable>

TARGET   claude-<model>
CONFIG   effort=<...> thinking=<...> <any hard constraint>
LAYER    spliced from references/models.md | none available for <model>
DISPATCH scoped session | subagent | run here | hand back only
```

`DISPATCH` is not decoration. Without it the prompt gets hand-executed wherever it lands, and
an investigation prompt hand-executed in the main thread has delivered the opposite of what it
was built for.

## Where this goes wrong

- **Splicing the wrong model's block.** The blocks contradict each other on purpose. A
  Sonnet-shaped prompt run on Fable does not error; it just quietly does something else.
- **Restating model capabilities from memory** because opening the reference felt slow. That
  is how a per-model claim goes stale in the one place people trust.
- **Shipping without the config.** The prompt then behaves differently for whoever runs it,
  and nobody can tell whether the prompt or the settings were wrong.
- **Over-formatting a small ask.** Twenty lines of scaffold on a one-line question is a cost
  paid for nothing.
- **Preamble.** The first line of output is the artifact.

## Definition of done

The prompt exists as copy-pasteable text, the resolved model target is stated outright, the
constraint block was spliced verbatim from the canon rather than recalled, and the request
config it assumes is named. A prompt the user still has to ask "which model is this for?"
about is not done.
