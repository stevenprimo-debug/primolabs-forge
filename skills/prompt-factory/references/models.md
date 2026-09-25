# Model-specific prompt templates — Opus 5 · Sonnet 5 · Fable 5

The per-model canon: the one place model-specific constraints live; write changes here first.

Built through `prompt-factory` over Anthropic's 7-tag engine, with the house voice layer
applied. Grounded in the official prompting/migration docs, hydrated via the `claude-api`
skill — not from training recall.

---

## The answer: same skeleton, different constraints

**The 7-tag structure does not change across models.** `<role>` `<task>` `<context>`
`<examples>` `<thinking>` `<constraints>` `<output>` is Anthropic's canonical shape and
nothing in the model-specific guidance touches it. Use only the tags the task warrants —
a tight 3-tag prompt beats a padded 7-tag one, on every model.

**What changes is the payload of `<constraints>`, and the request config around the prompt.**

And on two axes the models want **opposite** instructions. This is the part that bites if
you write one template and reuse it:

| Axis                | Opus 5                                                                   | Fable 5                                                                                      |
| ------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Subagent delegation | **Cap it** — delegates too readily, each subagent re-establishes context | **Encourage it** — parallel subagents are dependable; prefer async over spawn-and-block      |
| Process detail      | Tolerates structure                                                      | **De-prescribe** — step-by-step written for prior models measurably _reduces_ output quality |

A prompt tuned for Opus 5 and pointed at Fable 5 will suppress the delegation Fable is
good at and over-script a model that does better with goals than steps. The reverse leaves
Opus 5 spawning subagents it didn't need.

---

## Shared skeleton (all three models)

```xml
<role>
Who Claude is for this task — expertise, audience, accountability.
One or two sentences. A bare "You are a helpful assistant" is not a role.
</role>

<task>
One objective, with a success criterion. One task, one output.
State what "done" looks like, not the steps to get there.
</task>

<context>
Background Claude cannot infer: the product, the audience, the environment,
the quality bar, the reasons behind constraints. Long documents at the top,
the actual query at the end.
Context is never cruft — this is the tag to over-fill, not under-fill.
</context>

<examples>
3-5 input/output pairs covering normal and edge cases. The highest-leverage tag.
Label them illustrative. Vary them deliberately — a single "gold" example gets
matched for length, tone, and structure, freezing that shape into every output.
</examples>

<thinking>
Only for reasoning-heavy tasks, and see the per-model note below —
on Fable 5 this tag is usually unnecessary and the API parameter is forbidden.
</thinking>

<constraints>
Hard always/never rules, each with its reason. Plus: "if you are about to break
one of these, stop and say so rather than working around it."
This is where the model-specific block goes — see below.
</constraints>

<output>
Exact format, structure, and wrapper. State the shape, not a word count.
</output>
```

---

## The house layer — goes in `<constraints>` on every model

A house voice layer, applied in `<constraints>` on every model:

```xml
<constraints>
Never use: synergy · deep dive · circle back · unpack (as a verb) · elevate ·
empower · leverage (as filler verb) · transformative · innovative · best-in-class ·
move the needle · bandwidth (as metaphor) · crush it · 10x · level up · hustle.

Never open with: "Great question" · "Certainly!" · "Let's dive in" · "I'd be happy to" ·
"Here are some thoughts" · "It's important to note" · "In today's [adjective] world".
Never close with "Happy to help" or "Let me know if you have any other questions".

No warmth-as-default, no hedging-as-default, no meta-narration ("Let me break this
down"). Show the work, don't announce it. Hedge only on actual uncertainty.

Prose first. Bullets only for genuinely parallel items; tables only for real
row-and-column comparison. No mid-response section headers in conversational replies.
</constraints>
```

---

## Opus 5 — `claude-opus-5`

Add to `<constraints>`:

```xml
Keep responses focused and concise. Put most of the response on the main answer;
keep disclaimers and caveats brief. When asked to explain something, give a
high-level summary unless an in-depth one was requested.

Match the length of written deliverables — especially Markdown files — to what the
task needs. Do not pad documents with filler sections, redundant summaries, or boilerplate.

Deliver what was asked, at the scope intended. Make routine judgment calls yourself;
check in only when different readings lead to materially different work. If you think
the ask is mistaken, say so in a sentence and keep going with it as asked. Finish the
whole task — report completion only when it is fully done.

Subagents multiply cost and latency: each re-establishes context, re-explores, and
reports back. Delegate only when the payoff clearly exceeds that overhead — genuinely
independent, sizeable tracks. Never use subagents to verify or double-check your work;
verification belongs in your main loop. Keep spawn counts low.
```

**Delete from any prompt you migrate to Opus 5:** every "verify your work", "double-check
your answer", "include a final verification step" instruction. Opus 5 verifies unprompted;
telling it to causes over-verification, and removal costs no capability. This inverts the
usual self-check best practice — carve it out rather than applying that advice globally.

**Config:** thinking is ON by default (omitting the parameter runs adaptive). `{"type":
"disabled"}` is accepted only at effort `high` or below — pairing it with `xhigh`/`max`
returns a 400. Start at `high`, the API default, and adjust on your evals: step _up_ to
`xhigh` for demanding coding and agentic work, and to `max` where the task justifies
unconstrained token spend. `low` and `medium` are unusually strong here — use them
liberally as your primary control on token cost and response time wherever your evals show
quality holds. Prior-model defaults rarely transfer; run a fresh effort sweep rather than
carrying settings over. At `xhigh`/`max`, set `max_tokens` to at least 64K. No `temperature`/`top_p`/
`top_k`. No assistant prefill. Prompt-cache minimum drops to 512 tokens.

---

## Sonnet 5 — `claude-sonnet-5`

Add to `<constraints>`:

```xml
Apply each instruction at the scope stated. Where a rule should apply broadly, it says
so explicitly — do not narrow it to the first instance, and do not generalize a rule
beyond the scope given.

[If tools are available and under-used:] Call [tool] when [specific trigger condition].
Do not answer from prior knowledge when the answer depends on information the tool holds.
```

**Sonnet 5 follows instructions literally** — more so than 4.6. Holdover style and tone
directives now apply at face value, so re-baseline anything carried over rather than
assuming it still lands the same way. State scope explicitly where a rule should generalize.

**Drop** forced progress-update scaffolding ("summarize after every N tool calls") — the
default updates are better than the scaffold.

**Config:** adaptive thinking on by default. Effort defaults to `high`; raise to `xhigh`
for the hardest coding and agentic work. New tokenizer produces ~30% more tokens for the
same text than Sonnet 4.6, so re-baseline `max_tokens` and cost dashboards — per-token
price is unchanged. Non-default `temperature`/`top_p`/`top_k` are rejected. No prefill.
With thinking _disabled_ it becomes noticeably less tool-eager — add an explicit tool
nudge if you run it that way.

---

## Fable 5 — `claude-fable-5`

Add to `<constraints>`:

```xml
When you have enough information to act, act. Do not re-derive facts already established,
re-litigate a decision already made, or narrate options you will not pursue.
If weighing a choice, give a recommendation, not a survey.

Before reporting progress, audit each claim against a tool result from this session.
Report only work you can point to evidence for; if something is not yet verified, say so.
If tests fail, say so with the output. If a step was skipped, say that.

Don't add features, refactor, or introduce abstractions beyond what the task requires.
A bug fix doesn't need surrounding cleanup. Don't add error handling for scenarios that
cannot happen. Do the simplest thing that works.

When the user is describing a problem or thinking out loud rather than requesting a
change, the deliverable is your assessment — report findings and stop. Don't apply a fix
until asked. Before any command that changes system state, check the evidence supports
that specific action.

Delegate independent subtasks to sub-agents and keep working while they run. Intervene
only if one goes off track or is missing context.
```

**Do not write step-by-step process blocks for Fable 5.** State the goal, the constraints,
and how to verify. Prompts and skills written for prior models are often too prescriptive
here and reduce output quality — if you are migrating a prompt, A/B it with the older
scaffolding removed.

**Do not tell Fable 5 to reproduce its reasoning in the response.** An instruction to echo,
transcribe, or explain its internal reasoning as response text can trip the
`reasoning_extraction` refusal category, which shows up as elevated fallbacks to Opus 4.8.
Audit migrated prompts and skills for reflection or show-your-thinking lines. If you need
reasoning visibility, read the structured `thinking` blocks instead of asking for a retelling.

**Config:** thinking is always on — **omit the `thinking` parameter entirely.** Both
`{"type": "disabled"}` and `{"type": "enabled", "budget_tokens": N}` return a 400. The raw
chain of thought is never returned; `display: "summarized"` gives a readable summary.
Control depth with `output_config.effort` (`low` through `max`) — low and medium here often
beat prior models at `xhigh`. No sampling params, no prefill. **Requires 30-day data
retention** — a zero-retention org gets a 400 on every request regardless of payload.
Handle `stop_reason: "refusal"` before reading `content`, and opt into `fallbacks`.
$10/$50 per MTok against Opus 5's $5/$25, and single requests on hard tasks run many
minutes — plan timeouts and progress UX.

---

## Picking a model

Fable 5 is for the most demanding reasoning and long-horizon autonomous work — overnight
runs, first-shot implementation of well-specified systems, enterprise deliverables,
parallel subagent coordination. Its documented strengths do not include design or creative
judgment. Give it your hardest unsolved problem, at the top of your difficulty range;
routine work is a waste of the price difference.

Opus 5 is the default for complex agentic coding and everything else. Sonnet 5 reaches
near-Opus quality on coding and agentic work at lower cost.
