#!/usr/bin/env python3
"""
discover.py -- inventory a brand's source materials from LOCAL files, connector-optional.

The first stage of the brand pipeline. It answers "what have we already got to learn this
brand's voice from?" by scanning the repo/vault for the files that usually carry voice
signal -- existing brand tokens, a prior voice guideline, READMEs, about/marketing copy,
prose docs, shipped deliverables -- and grouping them by how strong a signal each is
likely to carry. It is deliberately LOCAL-FIRST: it never requires an enterprise
connector. When document, wiki, design, chat, or call-transcript connectors are present,
they enrich discovery, but their absence degrades to "local only" instead of failing.

Also reports whether a voice.json ALREADY resolves for the active client (via the sibling
brand-guideline resolver), so the next stage knows whether it is creating or updating.

Stdlib only. No network. Read-only -- it lists paths, it does not open connectors itself;
the model decides which discovered files to actually read.

Usage:
    python discover.py                     # scan the vault root, human report
    python discover.py --root <dir>        # scan an explicit root
    python discover.py --json              # machine-readable inventory
    python discover.py --client acmeco     # report voice.json state for a specific client
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# Dirs never worth scanning for brand signal.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".runtime", "_archive", "vendor",
    "dist", "build", ".next", ".venv", "venv", ".cache", "worktrees",
}

# Filename / path heuristics -> signal bucket. Ordered strongest-first; first hit wins.
# Kept generic and brand-agnostic: no vendor names, no client names.
SIGNAL_RULES = [
    ("voice-guideline", re.compile(r"voice(\.json|-guidelines?|_guidelines?)|tone-?of-?voice|style-?guide", re.I)),
    ("brand-tokens", re.compile(r"(^|/)brand\.json$|brand-?kit|brand-?guidelines?", re.I)),
    ("about-positioning", re.compile(r"(^|/)(about|positioning|messaging|manifesto|mission|values)", re.I)),
    ("marketing-copy", re.compile(r"(^|/)(marketing|copy|landing|homepage|hero|taglines?)", re.I)),
    ("deliverable", re.compile(r"(^|/)(deliverables?|proposals?|case-?stud|one-?pager)", re.I)),
    ("readme", re.compile(r"(^|/)readme(\.|$)", re.I)),
    ("prose-doc", re.compile(r"\.(md|markdown|txt|rst)$", re.I)),
]

# Connector CATEGORIES that COULD enrich discovery when available. Named by capability,
# not by vendor, so the skill stays brand- and vendor-agnostic and never hard-depends on
# any one integration. Absence is fine -- discovery runs local-only.
CONNECTOR_CATEGORIES = [
    "document store (shared docs / wiki / knowledge base)",
    "design source (component library / style files)",
    "team chat history",
    "call or meeting transcripts",
    "cloud file storage",
]

CONTENT_EXT = {".md", ".markdown", ".txt", ".rst", ".json", ".html"}
MAX_FILES = 400  # cap the report so a huge repo does not produce an unusable wall


def find_vault_root(start: str | None = None) -> str:
    """Walk up until a dir contains BOTH 'agents' (or .claude/agents) and '.claude'.

    Mirrors the resolver's root logic so discovery scans the same tree the resolver reads
    from. Falls back to the current working directory when no vault marker is found (a
    plain client repo), so discovery still works outside a core-vault layout.
    """
    d = os.path.abspath(start or os.getcwd())
    if os.path.isfile(d):
        d = os.path.dirname(d)
    probe = d
    while True:
        if os.path.isdir(os.path.join(probe, ".claude")) and (
            os.path.isdir(os.path.join(probe, "agents"))
            or os.path.isdir(os.path.join(probe, ".claude", "agents"))
        ):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return d  # no vault marker; scan where we started
        probe = parent


def classify(rel_path: str) -> str | None:
    """Return the signal bucket for a path, or None if it is not a content file."""
    posix = rel_path.replace("\\", "/")
    if Path(posix).suffix.lower() not in CONTENT_EXT:
        return None
    for bucket, pat in SIGNAL_RULES:
        if pat.search(posix):
            return bucket
    return None


def inventory(root: str) -> dict[str, list[str]]:
    """Walk `root`, returning {bucket: [relpath, ...]} for content files that match a rule."""
    buckets: dict[str, list[str]] = {}
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            bucket = classify(rel)
            if bucket is None:
                continue
            buckets.setdefault(bucket, []).append(rel.replace("\\", "/"))
            count += 1
            if count >= MAX_FILES:
                buckets.setdefault("_truncated", []).append(f"stopped at {MAX_FILES} files")
                return buckets
    for v in buckets.values():
        v.sort()
    return buckets


def _resolve_voice_py() -> Path | None:
    """Locate the sibling brand-guideline skill's resolve_voice.py (plugin or vault layout)."""
    cands = []
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        cands.append(Path(env) / "skills" / "brand-guideline" / "resolve_voice.py")
    cands.append(Path(__file__).resolve().parent.parent / "brand-guideline" / "resolve_voice.py")
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


def voice_state(client: str | None) -> dict:
    """Report whether a real (non-neutral) voice.json already resolves for the client."""
    resolver_py = _resolve_voice_py()
    if resolver_py is None:
        return {"resolver": "unavailable", "path": None, "exists": False}
    try:
        spec = importlib.util.spec_from_file_location("resolve_voice", str(resolver_py))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        path = mod.resolve_voice_path(client)
        # A resolved path that is a per-client file (under clients/) counts as "exists";
        # a .example fallback means no real guideline yet.
        is_real = bool(path) and "voice.json.example" not in os.path.basename(path or "")
        return {"resolver": "ok", "path": path, "exists": is_real}
    except Exception as e:
        return {"resolver": f"error: {e}", "path": None, "exists": False}


def build(root: str, client: str | None) -> dict:
    return {
        "root": root,
        "voice": voice_state(client),
        "connectors": {"detected": "not probed (local-first)", "categories_that_help": CONNECTOR_CATEGORIES},
        "local_sources": inventory(root),
    }


def format_report(data: dict) -> str:
    out = [f"brand discovery: {data['root']}"]
    v = data["voice"]
    if v["exists"]:
        out.append(f"voice.json: EXISTS -> {v['path']}  (guideline stage will UPDATE)")
    else:
        out.append(f"voice.json: none yet (guideline stage will CREATE; resolver={v['resolver']})")
    sources = data["local_sources"]
    total = sum(len(x) for k, x in sources.items() if k != "_truncated")
    out.append(f"\nlocal sources found: {total}")
    order = ["voice-guideline", "brand-tokens", "about-positioning", "marketing-copy", "deliverable", "readme", "prose-doc"]
    for bucket in order:
        files = sources.get(bucket)
        if not files:
            continue
        out.append(f"\n  {bucket} ({len(files)}):")
        for f in files[:12]:
            out.append(f"    - {f}")
        if len(files) > 12:
            out.append(f"    ... +{len(files) - 12} more")
    if sources.get("_truncated"):
        out.append(f"\n  NOTE: {sources['_truncated'][0]}")
    out.append("\nconnectors (optional -- discovery ran LOCAL-FIRST, none required):")
    for c in data["connectors"]["categories_that_help"]:
        out.append(f"    - {c}")
    out.append("\nNext: brand-guideline synthesizes these into clients/<client>/brand/voice.json.")
    return "\n".join(out)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root_arg = None
    client = None
    as_json = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root" and i + 1 < len(argv):
            root_arg = argv[i + 1]
            i += 2
        elif a == "--client" and i + 1 < len(argv):
            client = argv[i + 1]
            i += 2
        elif a == "--json":
            as_json = True
            i += 1
        else:
            i += 1
    root = find_vault_root(root_arg)
    data = build(root, client)
    if as_json:
        print(json.dumps(data, ensure_ascii=True, indent=2))
    else:
        print(format_report(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
