#!/usr/bin/env python3
"""
check.py -- deterministic voice check: scan copy against the active client's voice.json.

brand-police's mechanical half. It does the part a scanner does better than prose reading:
flag every banned term and every preferred-term swap in a piece of copy, with line and
column, so the model-driven rewrite starts from a complete, repeatable list instead of a
best-effort skim. The judgement half (tone, structure, on-brand vs off-brand feel) stays
with the model reading SKILL.md; this script owns only what is literally enumerable.

Resolves the voice guideline the brand-agnostic way, by sibling-loading resolve_voice.py
from the brand-guideline skill (the same importlib idiom corpus-html-index uses for
brand-resolver). On a shipped copy with no clients/ tree the resolver falls back to the
neutral example, so this runs anywhere without crashing -- it just has nothing to flag.

Stdlib only. No network.

Usage:
    python check.py <file>                 # scan a file, human report, exit 1 on violations
    python check.py <file> --json          # machine-readable findings
    python check.py --client acmeco <file> # scan against an explicit client's voice
    cat draft.md | python check.py -        # scan stdin
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path


def _resolve_voice_py() -> Path | None:
    """Locate the sibling brand-guideline skill's resolve_voice.py, portable across a
    plugin install and a core-vault checkout: env CLAUDE_PLUGIN_ROOT first, then
    sibling-relative (both are skills/ siblings), then the core-vault path."""
    cands = []
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        cands.append(Path(env) / "skills" / "brand-guideline" / "resolve_voice.py")
    cands.append(Path(__file__).resolve().parent.parent / "brand-guideline" / "resolve_voice.py")
    # walk up for a .claude/skills layout (core-vault checkout)
    here = Path(__file__).resolve()
    for anc in here.parents:
        cand = anc / ".claude" / "skills" / "brand-guideline" / "resolve_voice.py"
        if cand.is_file():
            cands.append(cand)
            break
    for c in cands:
        if c.is_file():
            return c
    return None


def load_active_voice(client: str | None, start: str | None = None) -> tuple[dict, str]:
    """Load the active voice guideline via the sibling resolver, or a bare neutral dict
    if the resolver skill is somehow absent.

    `start` seeds the resolver's vault-root walk at the operator's CWD (or the scanned
    file's dir), NOT the resolver's own __file__. A plugin-installed copy lives under
    ~/.claude/plugins/... which has no vault-root ancestor, so a __file__-anchored walk
    falls off the top and always resolves the shipped neutral example -- the exact reason
    brand-police was enforcing the neutral default instead of the real client/house voice.
    """
    resolver_py = _resolve_voice_py()
    if resolver_py is not None:
        try:
            spec = importlib.util.spec_from_file_location("resolve_voice", str(resolver_py))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.load_voice(client, start=start or os.getcwd())
        except Exception:
            pass
    # Last-ditch neutral so the scanner never crashes; matches the resolver's shape.
    return (
        {"banned_terms": [], "preferred_terms": [], "brand": {"name": "Your Brand"}},
        "<neutral: resolver unavailable>",
    )


def _iter_matches(text: str, phrase: str):
    """Yield (line, col, matched_text) for each case-insensitive occurrence of `phrase`.

    Whole-word for single tokens (so 'use' does not match 'used'); substring for
    multi-word phrases (so 'in order to' matches inside a sentence). Lines and columns
    are 1-based for human reports.
    """
    phrase = phrase.strip()
    if not phrase:
        return
    if re.search(r"\s", phrase):
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    else:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
    for m in pattern.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        col = m.start() - (text.rfind("\n", 0, m.start())) if "\n" in text[: m.start()] else m.start() + 1
        yield line, col, m.group(0)


def scan(text: str, voice: dict) -> list[dict]:
    """Return a flat list of findings against the voice guideline's enumerable rules."""
    findings: list[dict] = []
    for entry in voice.get("banned_terms", []) or []:
        term = (entry or {}).get("term", "")
        for line, col, hit in _iter_matches(text, term):
            findings.append(
                {
                    "kind": "banned",
                    "line": line,
                    "col": col,
                    "match": hit,
                    "reason": entry.get("reason", ""),
                    "suggest": entry.get("suggest", ""),
                }
            )
    for entry in voice.get("preferred_terms", []) or []:
        bad = (entry or {}).get("instead_of", "")
        good = (entry or {}).get("use", "")
        for line, col, hit in _iter_matches(text, bad):
            findings.append(
                {
                    "kind": "prefer",
                    "line": line,
                    "col": col,
                    "match": hit,
                    "reason": f"prefer '{good}'",
                    "suggest": good,
                }
            )
    findings.sort(key=lambda f: (f["line"], f["col"]))
    return findings


def format_report(findings: list[dict], source_label: str, target: str) -> str:
    out = [f"voice check: {target}", f"guideline: {source_label}"]
    if not findings:
        out.append("\nCLEAN -- 0 enumerable violations. (Tone/structure still need a human/model read.)")
        return "\n".join(out)
    out.append(f"\n{len(findings)} finding(s):\n")
    for f in findings:
        tag = "BANNED" if f["kind"] == "banned" else "PREFER"
        sug = f" -> '{f['suggest']}'" if f["suggest"] else ""
        reason = f"  ({f['reason']})" if f["reason"] else ""
        out.append(f"  [{tag}] {f['line']}:{f['col']}  \"{f['match']}\"{sug}{reason}")
    return "\n".join(out)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    client = None
    as_json = False
    target = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--client" and i + 1 < len(argv):
            client = argv[i + 1]
            i += 2
            continue
        if a == "--json":
            as_json = True
            i += 1
            continue
        target = a
        i += 1
    if target is None:
        print("usage: check.py <file|-> [--client <name>] [--json]")
        return 2

    if target == "-":
        text = sys.stdin.read()
        target_label = "<stdin>"
    else:
        try:
            text = Path(target).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"cannot read {target}: {e}")
            return 2
        target_label = target

    # Anchor the vault search at the scanned file's dir (real file) or CWD (stdin), so the
    # resolver walks UP to the real vault instead of off the top of the plugin cache.
    anchor = os.path.dirname(os.path.abspath(target)) if target != "-" else os.getcwd()
    voice, source_label = load_active_voice(client, start=anchor)
    findings = scan(text, voice)

    if as_json:
        print(json.dumps({"target": target_label, "guideline": source_label, "findings": findings}, ensure_ascii=True, indent=2))
    else:
        print(format_report(findings, source_label, target_label))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
