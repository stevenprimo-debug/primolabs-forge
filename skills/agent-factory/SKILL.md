---
name: agent-factory
description: Author one subagent seat at .claude/agents/<name>.md -- decide agent-vs-skill, emit from the template, choose the tool grant, specify the return shape, validate. Use whenever the user says build an agent, make an agent, new agent, add a seat, create a subagent, spin up a reviewer, or describes work that wants a fresh isolated perspective. Also fires when someone asks whether a job should be an agent or a skill.
disable-model-invocation: true
metadata:
  docs: https://code.claude.com/docs/en/sub-agents
---

# Agent Factory

Builds ONE seat. A seat is a single file — `.claude/agents/<name>.md` — whose body is the
system prompt a subagent wakes up with. It sees that text and nothing else: no chat history,
no memory of why it was called.

That isolation is the entire reason to reach for an agent, and it is also the constraint that
decides most of what follows.

## Ground truth is Anthropic's live sub-agents doc

The frontmatter schema, tool names, and subagent behavior described below track
https://code.claude.com/docs/en/sub-agents. Vendors move faster than any cached summary,
and a stale field name usually fails _forward_ — Claude Code silently ignores it — which is
how drift becomes invisible. Before asserting that a field exists, that a tool name is
valid, or that a permission mode behaves a certain way, fetch the doc. When a claim in a
conversation comes from training rather than the page you read this session, say
**"From training, not a doc:"** so the user can check it.

## First, decide it is an agent at all

|             | Skill                                                   | Agent                                                                      |
| ----------- | ------------------------------------------------------- | -------------------------------------------------------------------------- |
| context     | runs in the main conversation, sees what was just said  | isolated; sees only its system prompt                                      |
| interaction | back-and-forth, can ask mid-task                        | autonomous, returns one result                                             |
| execution   | sequential                                              | several can run at once, blind to each other                               |
| good for    | interactive work, anything needing conversation context | fresh perspective, parallel review, keeping clutter out of the main thread |

Choose a **skill** instead when the work is simple, needs the conversation, is interactive, or
needs many tools. Those are the four ways an agent goes wrong.

The honest test: _will this thing ever need to ask a question halfway through?_ If yes, it is
a skill. An isolated subagent cannot ask, so the question becomes an assumption, and the
assumption is where the wrong answer comes from.

The payoff case is parallel dispatch — several reviewers at once, each blind to the others, so
none inherits another's framing. If you are building one seat that runs alone and talks to the
user, reconsider.

## Emit it

```
py -3 ${CLAUDE_PLUGIN_ROOT}/scripts/factory.py agent <slug> --desc "<router-rule description>" [--docs <url>]
```

The description is what routing runs on, so name concrete cases rather than a topic. `--docs`
is required when the body names a third-party service — declare the canonical URL and fetch it
at the moment of need rather than trusting recall.

Then fill every `{{...}}` slot. The scaffold is the start, not the finish.

## Choose the tool grant

`tools:` is a decision. Fewer tools is more focused and cheaper, and the right grant follows
from what the seat does:

- **Analyses and reports, changes nothing** → `Read, Glob, Grep`
- **Builds or edits files** → `Read, Write, Edit, Glob, Grep, Bash`

Take `Bash` only if it genuinely runs commands; `Write` only if it creates files. A uniform
grant across every seat is the tell that nobody decided.

## Specify what it returns

An agent hands back one result into a context the caller cannot inspect — no reasoning, no
follow-up, no watching it work. **The shape of that result is the entire interface.**

State the sections, their order, whether findings are ranked, and what "nothing found" looks
like. Unspecified output is why agent results come back inconsistent and have to be re-read.

## Pin the model only with a reason

An unpinned seat inherits, which is a legitimate choice. If you pin, the pin carries its
justification and its revert:

```
model: opus  # what this buys, naming the evidence -- not a vibe. REVERT: `sonnet`.
effort: high
```

Bare alias only, never a dated ID, so it floats to the newest of that family. A pin without a
reason cannot be re-litigated later, because nobody knows whether it was measured or inherited.

## Validate

```
py -3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py
```

Nine checks including frontmatter fields, the model-pin shape, and the scrap detector. It must
read CLEAN before the seat counts as built.

## Confirm it loaded — structure is not reachability

`validate.py` checks the shape of the file. It cannot check that Claude Code found it. Those
are different questions. A seat can be perfectly well-formed and still sit at a path Claude
Code never scans — it passes every structural check, and it is invisible anyway, with nothing
to tell you.

So the last step is observation, not inspection:

- **A skill** appears in the invocable listing by name as soon as it is written. Look for it.
- **An agent** appears in the available agent types.

If it does not appear, the file is on disk and dead — check the path before touching the
content. A malformed skill at the right path is fixable; a perfect one at the wrong path is
invisible, and nothing errors to tell you.

## Where this goes wrong

- **Building an agent for work that needed a conversation.** The most common failure, because
  agents feel more substantial. The seat then guesses at the thing it should have asked.
- **Leaving the tool grant at whatever the template emitted.** It compounds: every seat gets
  Bash, and nothing is scoped.
- **Describing the output instead of showing it.** "Returns findings" is not a shape. The
  caller cannot see your reasoning, so anything you leave implicit is lost.
- **Writing the body by transforming another agent's body.** Mechanical porting carries the
  apparatus you meant to leave behind — that is how a retired concept survives a cleanup.
  Author it against what the seat actually does.

## Definition of done

The file exists at `.claude/agents/<slug>.md`, every `{{...}}` slot is filled, the tool grant
was chosen rather than inherited, the return shape is stated concretely, any model pin carries
a reason and a revert, `validate.py` reads CLEAN, and the seat appears in the available
agent types — observed, not assumed.
