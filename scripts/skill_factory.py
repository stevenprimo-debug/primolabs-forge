#!/usr/bin/env python3
"""
skill_factory.py -- the deterministic engine behind the house Skill Factory.

Internal meta-tooling (not shipped). Stdlib-only (no pip deps).
Drives the source-preservation contract that makes a rebuilt skill STRICTLY DEEPER
than its source: rebuilt output must preserve every source section header. The failure
it prevents: a long source skill rebuilt as a short ceremony shell that drops nearly all
the source's distinctive depth.

Subcommands:
  headers  --file <p>                              list real section headers (code-block "#" ignored)
  verify   --source <s> --output <o> [--json]      the source-preservation gate (exit 0 pass / 1 fail)
  scaffold --slug <s> --owner <o> --purpose <p>    emit a house atomic-skill skeleton
           [--source <path>] --out <dir>

Source is ASCII-clean on purpose (PS 5.1 + cross-platform safety). The .md it writes
uses ASCII punctuation ("--" not an em-dash) so emitted skills never trip the ASCII rule.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

# Human-readable output (headers/verdict) may echo a source header that contains
# accented characters. On a cp1252 / strict / redirected console (a caller that
# captures this stdout) a raw non-ASCII byte is mojibake at best and a
# UnicodeEncodeError at worst -- which would surface a perfectly valid unicode
# source as a spurious GATE FAILURE upstream. Make stdout/stderr tolerant so the
# house ASCII rule and the gate are never mutually exclusive (BUG-3).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")  # py3.7+
    except Exception:  # pragma: no cover - very old / wrapped stream
        pass


# ---------------------------------------------------------------------------
# header extraction (code-block aware)
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADER_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def extract_headers(text):
    """
    Return a list of section-header strings (the text AFTER the #'s), in document
    order, IGNORING any "#"-prefixed line that sits inside a fenced code block.
    A future Claude rebuilding a skill must preserve these -- code-comment "#"
    lines are not real sections and must not be forced into the rebuild.
    """
    headers = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADER_RE.match(line)
        if m:
            headers.append(m.group(2).strip())
    return headers


def _fold_accents(s):
    """NFKD-decompose then drop combining marks: 'Setup' stays, 'Resume' == 'Resume'.

    The house rule is ASCII-clean output; a faithful house rebuild of an accented
    source (e.g. a section titled with an accented word) is therefore re-authored
    in ASCII. Without folding, the gate would demand the accented byte survive --
    making the ASCII rule and the survival gate mutually exclusive (BUG-3). Fold
    BOTH sides so an ASCII rebuild of an accented header is correctly counted as
    preserved.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def normalize_header(h):
    """
    Normalize a header for survival comparison: drop leading #'s if present, drop a
    leading slash (so '/kb-article' matches 'KB Article'), NFKD-fold accents,
    lowercase, collapse internal whitespace, strip surrounding punctuation/space.
    Strict on the core noun phrase, lenient on decoration + accent encoding.
    """
    h = h.strip()
    h = re.sub(r"^#{1,6}\s*", "", h)  # in case a raw '# x' was passed
    h = h.lstrip("/").strip()
    h = _fold_accents(h)
    h = h.lower()
    h = re.sub(r"\s+", " ", h)
    h = h.strip(" \t:#-_*")
    return h


# ---------------------------------------------------------------------------
# the source-preservation gate
# ---------------------------------------------------------------------------


def _has_house_layer(out_text):
    """Detect the house layer the Skill Factory is contractually required to ADD on
    top of the preserved source (source PLUS house = strictly deeper).

    A verbatim passthrough (source == rebuild, zero house layer) would otherwise
    sneak past a length gate that only checks 'longer' -- so the bar is source +
    house, not source alone (BUG-2). We require BOTH house markers the house skill
    shell mandates: the TL;DR block and a stated Definition of done.
    Matched against the output's real header lines (code-block '#' ignored), folded
    + lowercased, so phrasing/case/accent variance does not defeat the check.
    """
    out_norm_headers = {normalize_header(h) for h in extract_headers(out_text)}
    has_tldr = any("tl;dr" in h or "for future claude" in h for h in out_norm_headers)
    has_done = any("definition of done" in h for h in out_norm_headers)
    return has_tldr, has_done


def verify(source_path, output_path):
    """
    Enforce source preservation on a rebuild. Returns a result dict.

    ONE gate: HEADERS. Every non-code-block source header must survive as a real section
    HEADER in the output -- matched against the output's extracted header set, NOT as a
    substring of arbitrary prose, so a casual mention of "setup" no longer counts as a
    preserved `## Setup` (BUG-1). Survival is counted by OCCURRENCES, so a rebuild that
    collapses two distinct source sections under one shared heading is caught as a drop
    (BUG-5).

    An empty source, or one with zero real headers, is itself a FAIL -- there is nothing
    to preserve, so a green verdict would be meaningless (BUG-4).

    A LENGTH gate and a LAYER gate were dropped, deliberately.

    The length gate required the output to be strictly longer than its source, on the
    premise that a rebuild always ADDS a house layer on top of preserved content. That
    premise is false here. Most of what a legacy file carries is removable -- superseded
    rulings, changelogs, dead pointers -- and the rebuilds that matter get SHORTER; a
    faithful rebuild can drop most of its bytes as archaeology while keeping every
    procedure, and the length gate fails exactly that work.

    Length cannot tell "I cut 15KB of history" from "I threw away the procedure."
    Header survival can, which is why it is the gate that stayed.

    The layer gate required a TL;DR and a Definition of done in the output. That is a
    template-completeness check, not a preservation check, and validate.py already owns
    structural conformance. Two checkers for one property is how they drift apart.
    """
    src_text = _read(source_path)
    out_text = _read(output_path)

    src_lines = src_text.splitlines()
    out_lines = out_text.splitlines()
    src_line_n = len(src_lines)
    out_line_n = len(out_lines)
    src_chars = len(src_text)
    out_chars = len(out_text)

    src_headers = extract_headers(src_text)

    # Build an OCCURRENCE multiset of the output's real header lines (code-block
    # '#' ignored). Matching a source header consumes one output occurrence so two
    # source sections cannot both be satisfied by a single surviving header (BUG-5).
    out_header_counts = {}
    for h in extract_headers(out_text):
        nh = normalize_header(h)
        if nh:
            out_header_counts[nh] = out_header_counts.get(nh, 0) + 1

    preserved = []
    dropped = []
    real_src_headers = 0
    for h in src_headers:
        nh = normalize_header(h)
        if not nh:
            continue
        real_src_headers += 1
        # survival = a matching real HEADER exists in the output, occurrence-counted
        if out_header_counts.get(nh, 0) > 0:
            out_header_counts[nh] -= 1
            preserved.append(h)
        else:
            dropped.append(h)

    total_headers = len(preserved) + len(dropped)

    # THE gate: every real source header preserved, AND the source actually HAD real
    # headers (an empty or 0-header source is meaningless -> FAIL, BUG-4).
    has_real_source = real_src_headers > 0 and src_chars > 0
    header_pass = has_real_source and len(dropped) == 0

    verdict = "PASS" if header_pass else "FAIL"

    return {
        "verdict": verdict,
        "header_pass": header_pass,
        "has_real_source": has_real_source,
        "source_lines": src_line_n,
        "output_lines": out_line_n,
        "source_chars": src_chars,
        "output_chars": out_chars,
        "total_source_headers": total_headers,
        "preserved_headers": preserved,
        "dropped_headers": dropped,
    }


def format_verdict(r):
    lines = []
    lines.append("VERDICT: %s" % r["verdict"])
    lines.append(
        "SIZE: source=%d lines (%d chars)  output=%d lines (%d chars)  -> not gated"
        % (r["source_lines"], r["source_chars"], r["output_lines"], r["output_chars"])
    )
    if not r.get("has_real_source", True):
        lines.append(
            "HEADERS: source has ZERO real section headers (or is empty) -> FAIL "
            "(nothing to preserve; gate is meaningless)."
        )
    else:
        lines.append(
            "HEADERS: %d/%d source headers preserved as real headers -> %s"
            % (
                len(r["preserved_headers"]),
                r["total_source_headers"],
                "PASS" if r["header_pass"] else "FAIL",
            )
        )
    if r["dropped_headers"]:
        lines.append("DROPPED:")
        for h in r["dropped_headers"]:
            lines.append("  - %s" % h)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# atomic-skill scaffold (from-scratch authoring skeleton -- Test A)
# ---------------------------------------------------------------------------

SCAFFOLD_TEMPLATE = """---
name: {slug}
description: >
  {purpose} TODO author the full pushy description: the exact trigger phrases that fire
  this skill, what it produces, what goes wrong without it, and the distinct-from neighbor.
  Never uses preamble; the first line of output IS the artifact.
type: skill
owner: {owner}
category: TODO-domain
version: "1.0.0"
status: scaffold
voice: BALANCED
source_path: {source}
created_by: skill-factory
# OPTIONAL FRONTMATTER -- all inherit / off by default; uncomment only as a DECISION.
# Verified against https://code.claude.com/docs/en/skills.md, fetched 2026-09-24. model/effort and
# the tool/context grants are turn-scoped -- they clear on the next user prompt.
# !! DISTRIBUTION -- upload (claude.ai / Skills API / package_skill.py) accepts ONLY name,
#    description, license, compatibility, metadata, allowed-tools. EVERY other key below is a HARD
#    ERROR on upload; uncommenting them makes the skill LOCAL-ONLY. allowed-tools survives upload.
#   model: opus   # bare alias opus/sonnet/fable, or `inherit`. Default: inherits session model.
#                 # A PIN IS A DECISION: carry WHY + REVERT (.claude/rules/model-pinning-and-subagents.md).
#   effort: high  # low|medium|high|xhigh|max. Overrides session effort. Default: inherits.
#   disable-model-invocation: true  # command-only (/{slug}); Claude will not auto-load it.
#   user-invocable: false           # Claude-only; hidden from the / menu (background knowledge).
#   allowed-tools: Read, Glob, Grep   # pre-approved while active (rule 7). UPLOAD-SAFE.
#   disallowed-tools: AskUserQuestion # removed while active (non-interactive loop). Local-only.
#   context: fork      # run in an ISOLATED subagent, NO history -- body must stand alone (rule 6).
#   agent: Explore     # which seat the fork uses (Explore/Plan/general-purpose or a .claude/agents/ seat).
#   background: false  # only with context:fork. false = wait in-turn + full tools; default true
#                      # backgrounds it, edits land OUTSIDE /rewind checkpoints.
#   paths: "src/**/*.ts"  # auto-load ONLY on matching files (orthogonal to description-firing).
#   argument-hint: "[issue]"  # autocomplete hint; arguments: [issue] enables $issue in the body.
#   when_to_use: >     # supplements description for triggering -- but PREFER description (single surface).
#     ...
# hooks: a skill CAN register session hooks on invoke -- NOT templated. Add one only on demonstrated
# need (CLAUDE.md hook-discipline); a stacked dead hook is invisible.
trigger: >
  Fire when the user says: TODO comma-separated trigger phrases.
inherits:
  - voice_spine: .claude/the voice rules.md
---

# {title}

## For future Claude (TL;DR -- read this first)

<3-5 load-bearing sentences. What this skill is, the one rule that governs it, the output
shape, and the single most common way it goes wrong. Runnable from this block alone.>

---

## Why this exists

<2-3 paragraphs of context: why this capability was worth making reusable, the in-the-wild
failure mode it prevents, who relies on its output.>

---

<!-- OPTIONAL: keep the Modes section ONLY if the skill has distinct invocation modes. -->
## Modes (optional)

- **`<mode-1>`** -- <one-liner>

---

## Step 1 -- <first imperative step>

<The procedure. Imperative voice, one verifiable action per step.>
{source_note}
## Step 2 -- <next step>

<...>

## Step N -- <final step>

<...>

---

## Anti-patterns (refuse list)

Inherits the voice rules section 4 (forbidden vocab + forbidden patterns). Plus:

- **Preamble.** First line of output IS the artifact. Never "Let me ...".
- **<skill-specific anti-pattern>** -- <correction>.
- **Forbidden vocab** per the voice rules section 4: elegant, premium, delightful, magical,
  deep dive, as an AI, great question, happy to help, let's dive in.

---

## Definition of done (universal)

Done means: the artifact exists at a named path (or the verdict is stated outright), every
factual claim in it was checked against the live system rather than assumed, and the next
action is named. Work you still have to verify is not done.

For {title} specifically: <the concrete done definition -- what artifact, at what path,
verified against what>.

---


- {today} -- scaffolded by skill-factory. <Author the body next.>


---
**Up:** [[agents/{dept}/_MOC|<Dept Display Name>]]
"""


def _description_safe(text):
    """Make a free-text purpose safe for the YAML `description` field.

    The validator (Anthropic, reused by quick_validate) hard-rejects ANY
    angle bracket in `description`. A purpose written with a common ASCII arrow
    convention ("A -> B") drops a literal '>' into the description
    and fails validation -- a valid-looking input producing an invalid artifact.
    The factory must never emit an invalid skill, so we normalize here:
    arrows -> the word 'to', then strip any remaining angle brackets. Applied
    ONLY to the description field; the body keeps the author's exact wording.
    """
    t = re.sub(r"\s*<-+>\s*|\s*<-+\s*|\s*-+>\s*", " to ", text)  # <->, <-, ->
    t = t.replace("<", "").replace(">", "")  # any stray brackets
    return re.sub(r"\s+", " ", t).strip()


def scaffold(slug, owner, purpose, source, out_dir):
    import datetime

    today = datetime.date.today().isoformat()
    title = " ".join(w.capitalize() for w in re.split(r"[-_]", slug) if w)
    dept = owner.split("/")[0].strip() if owner else "the-dept"
    src_field = source if source else "none"
    source_note = ""
    if source:
        source_note = (
            "\n<!-- SOURCE PRESERVED BELOW: %s -->\n"
            "<!-- Paste EVERY source section's content here VERBATIM, then add the house\n"
            "     layer on top. The verify gate refuses a write that is shallower than\n"
            "     the source or that drops a source header. -->\n" % source
        )

    body = SCAFFOLD_TEMPLATE.format(
        slug=slug,
        owner=owner,
        purpose=_description_safe(purpose.strip().rstrip(".")) + ".",
        source=src_field,
        title=title,
        dept=dept,
        source_note=source_note,
        today=today,
    )

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "SKILL.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    return path


# ---------------------------------------------------------------------------
# io + cli
# ---------------------------------------------------------------------------


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="skill_factory.py",
        description="house Skill Factory engine -- source-preservation gate + scaffold.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ph = sub.add_parser(
        "headers", help="list real section headers (code-block # ignored)"
    )
    ph.add_argument("--file", required=True)

    pv = sub.add_parser(
        "verify", help="source-preservation gate (exit 0 pass / 1 fail)"
    )
    pv.add_argument("--source", required=True)
    pv.add_argument("--output", required=True)
    pv.add_argument("--json", action="store_true")

    ps = sub.add_parser("scaffold", help="emit a house atomic-skill skeleton")
    ps.add_argument("--slug", required=True)
    ps.add_argument("--owner", required=True)
    ps.add_argument("--purpose", required=True)
    ps.add_argument("--source", default=None)
    ps.add_argument("--out", required=True)

    args = p.parse_args(argv)

    if args.cmd == "headers":
        for h in extract_headers(_read(args.file)):
            print(h)
        return 0

    if args.cmd == "verify":
        r = verify(args.source, args.output)
        if args.json:
            print(json.dumps(r, ensure_ascii=True, indent=2))
        else:
            print(format_verdict(r))
        return 0 if r["verdict"] == "PASS" else 1

    if args.cmd == "scaffold":
        path = scaffold(args.slug, args.owner, args.purpose, args.source, args.out)
        print("SCAFFOLDED: %s" % path)
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
