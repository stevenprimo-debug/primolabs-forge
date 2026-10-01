---
name: skill-factory
description: Interactively author ONE Claude Code skill by interview -- ask what the skill is, what "done" means, which frontmatter knobs to set, then scaffold it, write a small eval set, and run it to prove it works. Command-invoked only (/skill-factory). Use whenever the user says build a skill, make a skill, author a skill, new skill, turn this into a skill, or skillify this. Also fires when a workflow has been done twice by hand and should stop being re-derived.
disable-model-invocation: true
metadata:
  docs: https://code.claude.com/docs/en/skills
---

# Skill Factory

Builds ONE skill through a short **interview**. You invoke it with a command; it asks you a
handful of questions with `AskUserQuestion`, and each answer sets one decision — the trigger,
the definition of done, the model, whether it runs isolated, what it may touch, how it fires.
Then it scaffolds the folder, writes a small eval set, and **runs the new skill once** so you
see it work before it is called done.

The interview is the point. Answering "what is this, actually?" and "what does done look
like here?" out loud is what turns a vague idea into a skill that fires on the right thing and
stops at the right place. A skill dashed off without those answers is the one that never
triggers, or never knows when it is finished.

A skill is a folder — `.claude/skills/<name>/SKILL.md` plus optional siblings — that loads
into the _main_ conversation when it fires. It sees what was just said and can ask a question
mid-task, which is exactly what a subagent cannot. Reach for `agent-factory` instead when the
work wants isolation: a fresh reviewer, a parallel sweep, a verdict returned blind.

## Step 0 — root in the live docs, before the interview

Pull the current skills reference **before you build anything**, so every field and
frontmatter answer the interview gives is anchored in today's doc, not recall:

- **Pull the doc — API first, WebFetch fallback.** If the session has a docs/API skill (e.g.
  `claude-api`), use it; it reads the current page through the API. Otherwise fall back to
  `WebFetch https://code.claude.com/docs/en/skills` (the built-in fetch tool — no plugin or API
  needed). From the page, read the frontmatter schema, the `metadata:` policy, the description
  + `when_to_use` 1,536-char cap, the upload-safe key allowlist, and the load paths.
- The schema is not derivable from training — Anthropic's upload check hard-errors on unknown
  keys, and which keys survive an upload is stated only on the page. Ground the interview's
  frontmatter guidance in what you just pulled, not in this file's summary of it.
- **If neither path can pull the doc, STOP — do not author from training.** Say what unblocks
  it and wait. No live doc, no build.

Ground truth is the live page, not this file; where they disagree, the doc wins. Same rule for
any third-party service the skill names — declare it in `--docs` and fetch at the moment of
need (a wrong API version fails _forward_, behaving differently instead of erroring).

## The interview

Run these in order with `AskUserQuestion`. Carry each answer forward; a later question is
often answered by an earlier one, so don't re-ask what you already know. If the user invoked
the command with a description already typed, use it to pre-fill and skip ahead.

**1 — What are you turning into a skill?** Ask them to describe it in their own words, and
what kind of thing it is: a repeatable **workflow**, a **check/review**, a **transform**
(in → out), or a **reference** the model should consult. Take their prose and draft the
`description:` yourself — the pushy, trigger-first router rule below — then show it back and
confirm. Don't make them write frontmatter; make them describe the job.

**2 — What does "done" look like?** One or two sentences: the concrete end state, the artifact
produced, or the verdict returned. This becomes the skill's "Definition of done" and it also
seeds the eval set in step 8. If they can't say what done looks like, the skill isn't scoped
yet — help them narrow it before continuing.

**3 — Model & effort.** Do NOT ask them to pick a model cold — that is how the wrong one gets
assigned. **Default to inherit** (no pin) and say so; recommend a pin only when the skill's
nature clearly calls for it, and explain the recommendation in one line:

- Deep reasoning, adversarial review, architecture, hard judgment → recommend `model: opus`,
  `effort: high`.
- Everything mechanical, procedural, or short → inherit the session model (no pin). This is
  most skills.

Offer three options: **"Inherit (recommended for this)"**, **"Pin what I recommend"**, **"Let
me choose"**. A pin carries WHY + REVERT as a YAML comment; bare alias only (`opus`/`sonnet`/
`fable`), never a dated ID.

**4 — Run it isolated? (context fork).** Ask plainly: *"Should this run on its own, off to the
side — like sending an assistant to go do a job and report back — instead of in this
conversation?"* Most skills say no (they need the conversation). If **yes**, it becomes a
forked subagent and you set the chain:

- `context: fork` — runs with no conversation history, so the body must stand alone.
- `agent:` — which seat runs it: `Explore`, `Plan`, `general-purpose`, or one of your own
  `.claude/agents/` seats (e.g. an `account-manager` seat that can look an account up).
- `background:` — `false` waits for the result in this turn with full tools (usual choice);
  the default `true` backgrounds it, and those edits land outside `/rewind` checkpoints.

Example to make it concrete: an invoicing skill could fork to an `account-manager` seat that
goes and looks up the account, running in the background while you keep working. Powerful, but
only when the job truly doesn't need the conversation — offer it, don't push it.

**5 — What may it touch? (allowed tools).** Recommend from the job: reads-and-reports →
`Read, Glob, Grep`; edits files → add `Write, Edit, Bash`. `allowed-tools` pre-approves those
for the turn the skill runs, so the user isn't prompted mid-run. It is also the one advanced
key that survives an upload to the Skills API.

**6 — How should it fire?** *"Should Claude trigger this automatically when it's relevant, or
only when you type the command?"* Command-only sets `disable-model-invocation: true`. If it
should be a background capability Claude uses but never a menu item, that's `user-invocable:
false`. Default: auto-trigger on the description (leave both off).

**7 — Anything advanced? (optional, default skip).** Only if they ask: `paths:` to auto-load
on matching files, `arguments:` for `$name` substitution, `when_to_use:` to supplement the
trigger. Most skills need none of these — don't walk through them unprompted.

## The description is the product

It is the only part always in context, and it alone decides whether the skill ever fires.
Claude **under**-triggers, so write it pushy: say what the skill does _and_ name the contexts
and phrasings that should invoke it, including ones where the user never says the skill's name.

Weak — a topic: *"Author a case study."*
Strong — a router rule: *"Author a client case study end-to-end: gather sourced facts, draft,
render, hold for sign-off. Use whenever the user mentions a case study, a proof asset, a
client success story, or wants to show a prospect what an engagement produced — even without
the words 'case study.'"*

If you cannot name three phrasings that should fire it, it is not scoped yet — go back to
step 1.

## Emit the scaffold

With the interview answered, scaffold the folder:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/factory.py skill <slug> --desc "<the router-rule description>" [--docs <url>]
```

`--docs` is required once the body names a third-party service: declare the canonical URL and
fetch it at need rather than trusting recall — a wrong API version fails _forward_, behaving
differently instead of erroring.

Then open the emitted `SKILL.md` and **apply the interview answers to the frontmatter**. The
template ships every optional key commented out; uncomment and set only the ones the interview
chose (model/effort, `context`/`agent`/`background`, `allowed-tools`, invocation control).
Leave the rest commented — an inherited default is a real choice, not a gap.

## Structure the body

Fill every `{{...}}` slot. The shape comes from `templates/skill.md`:

- **What it does and why** — one paragraph; the reasoning, not just the steps. A model that
  understands _why_ handles the case you didn't anticipate.
- **Workflow** — imperative, numbered; where a step could be done another way, say why it's
  done this way.
- **Output format** — show the literal shape, not a description of it.
- **Examples** — one to three, concrete in and concrete out. Examples teach patterns more
  reliably than rules.
- **Where this goes wrong** — name the failure and its _mechanism_, not a bare prohibition.
  A stated mechanism survives paraphrase; "NEVER do X" gets rationalised around.

Keep the body under 500 lines; push long material into `references/`, executable work into
`scripts/` (executed, never loaded), output templates into `assets/`. Never name a sibling
that does not exist — a dead pointer promises depth that isn't there and nothing errors.

## Build the eval set — always, as part of the build

Every skill gets a small eval set, derived from the description (step 1) and the definition of
done (step 2). Write two or three realistic prompts a user would actually type, and what a
correct run produces, to `evals/evals.json`:

```json
{
  "skill_name": "<slug>",
  "evals": [
    { "id": 1, "prompt": "the kind of thing a user would actually type", "expected_output": "what a correct run produces", "files": [] }
  ]
}
```

For a skill whose output is a judgment call — voice, design, tone — the "expected_output" is
the shape and the checks a reviewer would apply, not an exact string. Don't force a brittle
assertion onto work that needs taste.

## Run it once — proof, not assumption

A skill that has never fired is a guess. Before calling it done, **run the new skill against
eval #1** and show the user the result:

- Fire it on the eval prompt (type its command, or let it trigger) and capture what it did.
- Compare against `expected_output`. If it fired on the right thing and stopped at the right
  place, it's real. If it didn't trigger, the description is the suspect (step 1); if it ran
  past "done", the definition of done is (step 2). Fix and re-run.

The run is the difference between "I wrote a file" and "I built something that works."

## Rebuilding an existing skill: the source-preservation contract

When you're absorbing or deepening an existing skill (a source file exists), **every section
of the source has to survive** — its procedures, tables, formulas, and worked examples come
across. Cutting the prose around them is expected; losing one of them is the failure.

Enumerate the source's sections first:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/skill_factory.py headers --file <source>
```

Author with every section carried across, then gate before writing:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/skill_factory.py verify --source <source> --output <draft>
```

**One gate: header survival.** Every source header must survive as a real header in the output
— not as a substring of prose. Matches are occurrence-counted, so collapsing two sections
under one heading is caught as a drop. An empty source, or one with zero headers, is itself a
FAIL. **Exit 1 means halt** — read the `DROPPED:` list, restore those sections, re-run. The
failure this prevents is specific and it happened: a 351-line source rebuilt as a 145-line
shell that kept 1 of 26 headers — it looked clean and had thrown away the content.
**Paraphrasing is dropping.** The house layer goes _on top of_ source content, never instead.

## Validate

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py
```

Checks the load path, body size, description presence, official frontmatter fields, declared
vendor docs under `metadata:`, undeclared network calls in bundled scripts, and the scrap
detector. CLEAN before it counts as built.

## Confirm it loaded — structure is not reachability

`validate.py` checks the shape of the file, not that Claude Code found it — different
questions. A skill can be perfectly well-formed and sit at a path nothing scans, passing every
structural check while invisible. So the last step is observation: a skill appears in the
invocable listing by name as soon as it is written. Look for it. If it doesn't appear, the
file is on disk and dead — check the path before touching the content.

## Where this goes wrong

- **Skipping the interview and dashing off a description.** The skill then never triggers, or
  never knows when it's done — the two failures the interview exists to prevent.
- **Writing a skill that should have been an agent.** If the work wants a cold second opinion
  or runs in parallel, the main conversation is the wrong place — use `agent-factory`.
- **A description that names a topic instead of trigger cases.** It exists and never fires,
  which looks identical to not having built it.
- **Never running the new skill.** "I wrote the file" is not "it works." The eval run is the
  proof.
- **Naming `references/` or `evals/` in the body without creating them.** Aspirational
  structure reads as real structure to the next session.

## Definition of done

The live skills doc was fetched this session and the field/frontmatter guidance came from it,
not training (no fetch → no build); the interview was answered (not skipped); the folder
exists at `.claude/skills/<slug>/`; the description names concrete trigger cases; the chosen
frontmatter knobs are set and the rest left inheriting; every `{{...}}` slot is filled;
`evals/evals.json` holds 2–3 real prompts;
the skill was **run against eval #1 and behaved**; `validate.py` is CLEAN; and the skill
appears in the invocable listing — observed, not assumed.
