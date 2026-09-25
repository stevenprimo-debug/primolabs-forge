#!/usr/bin/env python3
"""PrimoLabs architecture validator.

Written BEFORE the first agent exists, so it starts at zero and stays there.

Eight checks plus the scrap detector. It does NOT test behaviour -- it checks structure,
declarations and safety posture. A file can pass everything here and still be wrong; the
defence against that is review and real use, not a ninth check. Adding structural checks
until it feels safe is how a gate suite bloats.

    py -3 scripts/validate.py            # report, exit 1 on any finding
    py -3 scripts/validate.py --quiet    # exit code only
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Root resolution: CLAUDE_PROJECT_DIR (the user's repo) when the factory points us at
# the output it just wrote; otherwise this script's own repo/plugin (script-relative).
ROOT = Path(
    os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parent.parent
).resolve()
# Two layouts wear the same validator: a normal repo keeps seats under .claude/skills,
# a plugin keeps them at <root>/skills (per code.claude.com/docs/en/plugins-reference).
# Detect by which tree exists so the same file validates both without a mode flag.
if (ROOT / ".claude" / "skills").is_dir() or (ROOT / ".claude" / "agents").is_dir():
    AGENTS = ROOT / ".claude" / "agents"
    SKILLS = ROOT / ".claude" / "skills"
else:
    AGENTS = ROOT / ".claude" / "agents"
    SKILLS = ROOT / "skills"

# Official subagent frontmatter, per code.claude.com/docs/en/sub-agents (2026-08-10).
# `name` and `description` are the only required fields.
OFFICIAL_FIELDS = {
    "name",
    "description",
    "tools",
    "disallowedTools",
    "model",
    "permissionMode",
    "maxTurns",
    "skills",
    "mcpServers",
    "hooks",
    "memory",
    "background",
    "effort",
    "isolation",
    "color",
    "initialPrompt",
}
# Official SKILL frontmatter, per code.claude.com/docs/en/skills (2026-08-10). A different
# set from the subagent one above -- they are different artifacts and do not share fields.
# Note `metadata`: the sanctioned free-form map for your own keys. Skills put local
# extensions THERE, never at the top level.
SKILL_FIELDS = {
    "name",
    "description",
    "when_to_use",  # added 2026-08-14: documented in docs/en/skills (trigger context, appended to description)
    "arguments",  # added 2026-08-14: documented in docs/en/skills ($name substitution)
    "disallowed-tools",  # added 2026-08-14: documented in docs/en/skills
    "effort",  # added 2026-08-14: documented in docs/en/skills
    "argument-hint",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "model",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
    "metadata",
    "license",  # Agent Skills spec field, per docs/en/skills -- Claude Code accepts it, does not act on it
    "compatibility",  # Agent Skills spec field, per docs/en/skills -- environment requirements
}
# PrimoLabs additive metadata. Subagents have NO `metadata` field in the spec, so on an
# AGENT this stays a declared top-level extension; on a SKILL it belongs under `metadata:`.
# Declared so check 2 can tell "deliberate extension" from "typo".
LOCAL_FIELDS = {"docs"}

# Law 2: anything naming one of these must declare where its facts come from.
VENDOR_TOKENS = [
    "shopify",
    "bigcommerce",
    "stripe",
    "twilio",
    "resend",
    "asana",
    "vercel",
    "cloudflare",
    "supabase",
    "klaviyo",
    "shippo",
    "hubspot",
]

# Retired legacy concepts. A hit fails the build; waive with an inline marker carrying a
# REASON, on the same line:  <!-- scrap-ok: why -->  or  # scrap-ok: why
# No baselines file, no ratchet, no blanket file exclusions. If waivers start
# accumulating, that is the signal something dirty is being argued in.
SCRAP = {  # scrap-ok: this dict IS the deny list; the terms must appear to be matched
    "chief-of-staff seat": r"chief-of-staff|chief_of_staff",  # scrap-ok: deny-list pattern
    "ROOK architecture": r"\bROOK\b",  # scrap-ok: deny-list pattern
    "personality bench triplet": r"personality/_bench|frameworks_index|frameworks_attribution",  # scrap-ok: deny-list pattern
    "Director tier": r"Director:|dead-director|UPSTREAM clause",  # scrap-ok: deny-list pattern
    "Tier-N seat label": r"Tier:\s*[0-9]|Tier [0-9] \(",  # scrap-ok: deny-list pattern
    "retired routing manifest": r"routing-rules\.json",  # scrap-ok: deny-list pattern
    "retired capture pipeline": r"capture_routing_keywords|capture-pipeline",  # scrap-ok: deny-list pattern
    "gate ratchet system": r"gate-baselines|count_regex",  # scrap-ok: deny-list pattern
    # Added 2026-08-10 after the deny list MISSED this class. It caught the pointer to
    # that pointer file and completely missed the same apparatus written inline as a  # scrap-ok: explaining the miss
    # table. A deny list catches vocabulary, not concepts -- so when a concept slips
    # through, its vocabulary goes in.
    "bench/pole apparatus": r"\bPole\b|Tension axis|principles in productive tension|stage_debate",  # scrap-ok: deny-list pattern
    "1.4 memory doctrine": r"[Cc]ompounding-append",  # scrap-ok: deny-list pattern
    "non-loading seat path": r"agents/[a-z-]+/[a-z-]+/SKILL\.md|agents/[a-z-]+/skills/",  # scrap-ok: deny-list pattern
}
# Accepts the markdown comment form and the script comment form, because the ship set is
# markdown, Python and PowerShell. A marker with no reason after the colon does not waive.
SCRAP_OK = re.compile(r"(?:<!--|#)\s*scrap-ok:\s*\S.*")
MAX_SKILL_LINES = 500

findings: list[str] = []


def fail(check: str, path: Path, msg: str) -> None:
    rel = path.relative_to(ROOT).as_posix() if path.is_absolute() else str(path)
    findings.append(f"[{check}] {rel}: {msg}")


def metadata_block(text: str) -> dict[str, str]:
    """Read the one-level-deep `metadata:` map. Skills carry local extensions there --
    it is the only free-form key space the skill spec sanctions, and Claude Code drops
    the value entirely if it is not a map."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    inside = False
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] not in (" ", "\t"):
            inside = line.split(":", 1)[0].strip() == "metadata"
            continue
        if inside and ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip("'\"")
    return out


def frontmatter(text: str) -> dict[str, str] | None:
    """Minimal YAML frontmatter reader -- top-level `key: value` only, which is all the
    subagent contract uses. Deliberately not a YAML parser: a dependency here would have
    to ship to every client repo."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in (" ", "\t"):  # nested value, belongs to the key above
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def declared_skills(fm: dict[str, str]) -> list[str]:
    raw = fm.get("skills", "")
    return [s.strip().strip("'\"") for s in raw.strip("[]").split(",") if s.strip()]


# ---------------------------------------------------------------- checks 1-3, 6, 8
def check_agents() -> None:
    if not AGENTS.is_dir():
        return
    for p in sorted(AGENTS.rglob("*.md")):
        if p.parent != AGENTS:  # 1
            fail(
                "1 agent-location", p, "agents are flat in .claude/agents/, not nested"
            )
        text = p.read_text(encoding="utf-8-sig", errors="replace")
        fm = frontmatter(text)
        if fm is None:  # 2
            fail("2 agent-frontmatter", p, "no YAML frontmatter")
            continue
        for req in ("name", "description"):
            if not fm.get(req):
                fail("2 agent-frontmatter", p, f"missing required `{req}`")
        for key in fm:
            if key not in OFFICIAL_FIELDS | LOCAL_FIELDS:
                fail(
                    "2 agent-frontmatter",
                    p,
                    f"`{key}` is not an official subagent field (see docs/en/sub-agents)",
                )
        name = fm.get("name", "")
        if name and not re.fullmatch(r"[a-z0-9-]+", name):
            fail(
                "2 agent-frontmatter",
                p,
                f"name `{name}` must be lowercase letters/hyphens",
            )
        desc = fm.get("description", "")
        if desc and len(desc) < 40:  # 8
            fail(
                "8 trigger-precision",
                p,
                "description is too vague to route on -- name concrete cases",
            )
        for skill in declared_skills(fm):  # 5
            if not (SKILLS / skill / "SKILL.md").is_file():
                fail(
                    "5 named-skills-resolve",
                    p,
                    f"declares skill `{skill}` with no folder",
                )
        body = text.lower()
        if any(t in body for t in VENDOR_TOKENS) and not fm.get("docs"):  # 6
            hits = sorted({t for t in VENDOR_TOKENS if t in body})
            fail(
                "6 vendor-docs",
                p,
                f"names {', '.join(hits)} but declares no `docs:` URL (Law 2)",
            )
        check_model_pin(p, text, fm)  # 9


def check_model_pin(p: Path, text: str, fm: dict[str, str]) -> None:
    """Check 9 -- a pin carries a WHY and a REVERT.

    Earned its place by catching a real defect: an early version of the agent template
    hardcoded `model: sonnet` across every seat, discarding measured per-seat pins and
    their evidence. A pin without a reason is a guess with a version number.
    """
    pin = fm.get("model")
    if not pin:
        return  # unpinned is legitimate -- it inherits
    alias = pin.split("#")[0].strip()
    if alias not in {"opus", "sonnet", "fable"}:
        fail(
            "9 model-pin",
            p,
            f"`{alias}` must be a bare alias (opus/sonnet/fable), never a dated ID; "
            f"haiku is out of the roster",
        )
    # the reason may sit inline on the pin or on the comment lines beneath it
    block, on = [], False
    for line in text.splitlines():
        if re.match(r"^model:", line):
            on = True
            block.append(line)
            continue
        if on:
            if line.lstrip().startswith("#"):
                block.append(line)
            elif re.match(r"^effort:", line):
                continue
            else:
                break
    joined = " ".join(block)
    if "#" not in joined or len(joined.split("#", 1)[1].strip()) < 20:
        fail(
            "9 model-pin", p, "pin carries no WHY -- say what it buys, naming evidence"
        )
    if "REVERT:" not in joined:
        fail(
            "9 model-pin",
            p,
            "pin carries no `REVERT:` -- the one-line change that undoes it",
        )


def check_no_invented_folders() -> None:  # 3
    legacy = ROOT / "agents"
    if not legacy.is_dir():
        return
    for sub in ("memory", "context", "skills", "personality"):
        for hit in legacy.glob(f"*/{sub}"):
            fail(
                "3 invented-folder",
                hit,
                f"`agents/<name>/{sub}/` is not a path Claude Code loads from",
            )


# ---------------------------------------------------------------- checks 4, 6, 7
def check_skills() -> None:
    if not SKILLS.is_dir():
        return
    for skill_md in sorted(SKILLS.rglob("SKILL.md")):
        # VENDORED skills -- a _VENDORED.md beside SKILL.md -- are upstream's shape, not
        # ours (a maintainer ruling, admitting vendored packages like ui-ux-pro-max and the
        # official GSAP set). Their frontmatter, size and structure are the upstream author's choices,
        # and every finding against them is unactionable except "drop the package",
        # because hand-editing vendored files is forbidden. So the per-skill checks skip
        # them entirely; the _VENDORED.md pin (upstream, commit, license, pull date) is
        # the accountability artifact instead. A vendored skill that turns out to carry
        # something unacceptable gets REMOVED or re-pulled, never patched.
        if (skill_md.parent / "_VENDORED.md").exists():
            continue
        if skill_md.parent.parent != SKILLS:  # 4
            fail(
                "4 skill-location",
                skill_md,
                "skills live one level deep: .claude/skills/<name>/SKILL.md",
            )
        text = skill_md.read_text(encoding="utf-8-sig", errors="replace")
        lines = text.count("\n") + 1
        if lines > MAX_SKILL_LINES:  # 4
            fail(
                "4 skill-size",
                skill_md,
                f"{lines} lines exceeds {MAX_SKILL_LINES} -- move detail to reference files",
            )
        fm = frontmatter(text) or {}
        meta = metadata_block(text)
        if not fm.get("description"):  # 8
            fail("8 trigger-precision", skill_md, "no `description` to route on")
        for key in fm:  # 2
            if key not in SKILL_FIELDS:
                where = (
                    "move it under `metadata:` -- the sanctioned free-form map"
                    if key in LOCAL_FIELDS
                    else "not an official skill field (see docs/en/skills)"
                )
                fail("2 frontmatter", skill_md, f"`{key}`: {where}")
        # Law 2 reads from metadata on a skill; agents keep `docs:` top-level because the
        # subagent spec has no metadata field.
        declared = meta.get("docs", "")
        if any(t in text.lower() for t in VENDOR_TOKENS) and not declared:
            hits = sorted({t for t in VENDOR_TOKENS if t in text.lower()})
            fail(
                "6 vendor-docs",
                skill_md,
                f"names {', '.join(hits)} but declares no `metadata.docs` URL (Law 2)",
            )
        for script in skill_md.parent.rglob("*.py"):  # 7
            body = script.read_text(encoding="utf-8-sig", errors="replace")
            for host in re.findall(r"https?://([A-Za-z0-9.-]+)", body):
                if host not in declared:
                    fail(
                        "7 safety-posture",
                        script,
                        f"calls {host}, undeclared in `metadata.docs`",
                    )


# ---------------------------------------------------------------- scrap detector
def check_scraps() -> None:
    # Imported historical corpora and transcript content are skipped: they legitimately
    # quote retired vocabulary the scrap detector would otherwise flag as live wiring.
    # A transcript that quotes someone using a retired term is content, not a reference  # scrap-ok: naming the retired thing is what this comment explains
    # to a retired concept, and no amount of hand-editing keeps such corpora clean of the
    # vocabulary they exist to capture.
    skip = {
        ".git",
        "node_modules",
        "_archive",
        ".runtime",
        "vendor",
        "__pycache__",
        "memory-import",
        "yt-corpus",
        "worktrees",  # each .claude/worktrees/<name> is its own checkout + session;
        # vendored/cached reference docs there are scoped to that session, not this repo's canon
    }
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".md", ".py", ".ps1", ".json"}:
            continue
        if skip & set(p.relative_to(ROOT).parts):
            continue
        try:
            lines = p.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if SCRAP_OK.search(line):
                continue
            for label, pat in SCRAP.items():
                if re.search(pat, line):
                    fail("scrap", p, f"line {i}: retired concept `{label}`")
                    break


def main() -> int:
    check_agents()
    check_no_invented_folders()
    check_skills()
    check_scraps()

    quiet = "--quiet" in sys.argv
    if not quiet:
        print(f"PrimoLabs validator  --  root {ROOT}")
        n_agents = len(list(AGENTS.glob("*.md"))) if AGENTS.is_dir() else 0
        n_skills = len(list(SKILLS.glob("*/SKILL.md"))) if SKILLS.is_dir() else 0
        print(f"  agents: {n_agents}   skills: {n_skills}")
        if findings:
            print(f"\n{len(findings)} finding(s):\n")
            for f in findings:
                print("  " + f)
        else:
            print("\nCLEAN -- 0 findings.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
