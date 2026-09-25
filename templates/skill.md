---
name: '{{SLUG}}'
description: '{{DESCRIPTION}}'
# OPTIONAL FRONTMATTER -- all inherit / off by default; uncomment only as a DECISION.
# Verified against https://code.claude.com/docs/en/skills.md, fetched 2026-09-24. model/effort and
# the tool/context grants are turn-scoped: they apply while this skill is active and clear on the
# next user prompt; nothing is saved to settings.
# !! DISTRIBUTION -- uploading a skill (claude.ai / Skills API / package_skill.py) accepts ONLY
#    name, description, license, compatibility, metadata, allowed-tools. EVERY other key below is a
#    HARD ERROR on upload, so uncommenting model/effort/disable-model-invocation/user-invocable/
#    context/paths/arguments/when_to_use/disallowed-tools makes the skill LOCAL-ONLY. allowed-tools
#    is the one advanced knob that survives upload. (This plugin ships as a git marketplace source,
#    which loads skills locally -- so pinned keys work here; the caveat is for API/package uploads.)
#
# -- model & effort -- a PIN IS A DECISION: carry WHY + REVERT (.claude/rules/model-pinning-and-subagents.md)
#   model: opus   # bare alias opus/sonnet/fable, or `inherit`. Default: inherits session model.
#   effort: high  # low|medium|high|xhigh|max. Overrides session effort. Default: inherits.
#
# -- invocation control --
#   disable-model-invocation: true  # command-only (/{{SLUG}}); Claude will not auto-load it.
#   user-invocable: false           # Claude-only; hidden from the / menu (background knowledge).
#
# -- tool scoping for the invoking turn (rule 7); grant/deny clears on the next message --
#   allowed-tools: Read, Glob, Grep   # pre-approved without a prompt while active. UPLOAD-SAFE.
#   disallowed-tools: AskUserQuestion # removed while active (e.g. a non-interactive loop). Local-only.
#
# -- run as an ISOLATED subagent (rule 6: fresh mind / parallel fan-out) --
#   context: fork      # forked subagent, NO conversation history -- the body must stand alone.
#   agent: Explore     # which seat the fork uses (Explore/Plan/general-purpose or a .claude/agents/ seat).
#   background: false  # only with context:fork. false = wait in-turn + full tools; default true
#                      # backgrounds it, and those edits land OUTSIDE /rewind checkpoints.
#
# -- situational (uncomment only when the skill needs it) --
#   paths: "src/**/*.ts, src/**/*.tsx"  # auto-load ONLY on matching files. Orthogonal to the
#                                       # description-is-the-trigger default; use for file-scoped skills.
#   argument-hint: "[issue] [branch]"   # autocomplete hint (command-style skills).
#   arguments: [issue, branch]          # positional $issue / $branch substitution in the body.
#   when_to_use: >                      # supplements description for triggering -- but PREFER
#     ...                               # description (the authoring notes make it the single trigger surface).
#
# hooks: a skill CAN register session hooks on invoke -- deliberately NOT templated. Add one only when
# a session DEMONSTRATES the absence (CLAUDE.md hook-discipline); a stacked dead hook is invisible.
metadata:
  docs: '{{DOCS_URL}}'
---

# {{TITLE}}

## TL;DR — read this first

{{TLDR}}

<!-- 3-5 load-bearing sentences: what this is, the one rule that governs it, the output
     shape, and the single commonest way it goes wrong. The bar: someone should be able to
     run this skill correctly from this block alone, without reading the rest. -->

## Why this exists

{{PURPOSE}}

<!-- One or two paragraphs. The failure mode in the wild that this prevents, and the
     reasoning behind the approach -- not just the steps. A model that understands WHY can
     handle the case you did not anticipate. Do NOT restate when to use it; that belongs in
     `description:`, which is the actual triggering mechanism. -->

## Workflow

{{WORKFLOW}}

<!-- Imperative form. Number the steps. For each one that could plausibly be done another
     way, say why it is done this way. skill-creator: "explain to the model why things are
     important in lieu of heavy-handed musty MUSTs." A step whose reason is stated survives
     paraphrase; a bare rule does not. -->

## Output format

{{OUTPUT}}

<!-- Show the literal shape, not a description of it. Sections, order, ranking, and what
     an empty result looks like. This is the one place a rigid template is correct -- the
     caller parses it. -->

## Examples

{{EXAMPLES}}

<!-- 1-3 worked examples. Concrete input, the actual output. Examples teach patterns far
     more reliably than rules do, and they are cheaper to get right. -->

## Where this goes wrong

{{FAILURE_MODES}}

<!-- Name each failure and the reason it happens, not a prohibition. "Numbers get quoted
     without their source because the source felt obvious while drafting -- it will not be
     obvious to the reader" beats "NEVER quote an unsourced number." State the mechanism
     and the rule follows; state the rule alone and it gets rationalized around.
     ALL-CAPS ALWAYS/NEVER is a yellow flag per skill-creator, not a style choice. -->

<!--
AUTHORING NOTES -- delete this block once the skill is written.
Source: Anthropic skill-creator.

DESCRIPTION IS THE PRODUCT. It is the only part always in context, and it alone decides
whether the skill fires. Claude UNDER-triggers, so be pushy: state what it does AND the
specific contexts and phrasings that should invoke it, including ones where the user does
not name the skill. Weak: "Author a case study." Strong: "Author a client case study --
gather sourced facts, draft, render, hold for sign-off. Use whenever the user mentions a
case study, a proof asset, a client success story, or wants to show a prospect what an
engagement produced, even if they don't use the words 'case study'."

PROGRESSIVE DISCLOSURE -- three levels:
  1. name + description   always in context
  2. SKILL.md body        loaded when it fires; keep under 500 lines
  3. bundled resources    loaded or executed only when pointed at

    .claude/skills/{{SLUG}}/
      SKILL.md        this file
      references/     long material, read on demand. >300 lines: add a table of contents
      scripts/        executed, never loaded into context
      assets/         templates, icons, fonts used in output
      evals/evals.json  test prompts

Point at siblings explicitly and say when to read each. Do NOT name a sibling that does
not exist -- a dead pointer in a fresh file is worse than no pointer.

EVALS. If the output is objectively checkable -- a file transform, an extraction, a fixed
verdict -- write 2-3 realistic test prompts to evals/evals.json and run them before
calling the skill done. Subjective skills (voice, design) are reviewed by eye instead.

  {"skill_name": "{{SLUG}}", "evals": [{"id": 1, "prompt": "...", "expected_output": "...", "files": []}]}

`docs:` on a SKILL lives under `metadata:` -- the sanctioned free-form map per
https://code.claude.com/docs/en/skills ("Free-form YAML map for your own key-value data,
such as entitlement or catalog fields, read by your own tooling from SKILL.md"). Top-level
`docs:` on a skill is rejected by Anthropic's own upload check with an unexpected-key
error, and by validate.py check 2. AGENTS keep `docs:` top-level because the subagent spec
has no `metadata` field; only skills nest it. validate.py LOCAL_FIELDS declares `docs` as
the one PrimoLabs extension so check 2 can tell deliberate from typo, and checks 6/7
enforce Law 2 against `metadata.docs` on skills and top-level `docs` on agents.
-->
