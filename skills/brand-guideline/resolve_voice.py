#!/usr/bin/env python3
"""
resolve_voice -- resolve the active client's voice.json by CLIENT, not by hardcoded path.

The voice guideline is the shared DATA contract for the three brand skills:
brand-discover feeds it, brand-guideline writes it, brand-police reads it. Like
brand.json (visual tokens), voice DATA is client-specific and lives under
clients/<client>/brand/ (which NEVER ships). The shippable tree carries only this
resolver + a brand-neutral voice.json.example default. No reader hardcodes a path to a
specific client's voice.json -- it asks this resolver for the active client's file, and
on a shipped copy (no clients/ tree) it falls back to the neutral example, then to an
in-code neutral dict.

Deliberately MIRRORS skills/brand-resolver/resolve_brand.py so voice and visual tokens
resolve for the SAME active client via identical logic. find_vault_root() and
active_client() are copied (not imported) so this file stands alone even if it is the
only brand skill installed -- two trivial pure functions, kept intentionally in step.

Resolution (first that exists wins):
  1. <vault_root>/clients/<active_client>/brand/voice.json   (canonical per-client; never ships)
  2. <vault_root>/.claude/voice.json.example                 (repo-level neutral; ships)
  3. <this dir>/voice.json.example                           (travels with the resolver)
  4. an in-code NEUTRAL_VOICE dict                            (last resort; always available)

Read as "the active client's voice, else the neutral default, else nothing." A public
copy with no clients/ tree resolves the neutral example, exactly like resolve_brand.py.

active_client precedence:  explicit arg -> env FORGE_ACTIVE_CLIENT -> default "default".

Stdlib only. No network. No state file.

Usage (library):
    from resolve_voice import resolve_voice_path, load_voice, validate_voice
    path      = resolve_voice_path()             # active client from env or default
    voice,src = load_voice("acmeco")             # (dict, "path or '<neutral>'")
    errors    = validate_voice(voice)            # [] means schema-conformant

Usage (CLI):
    python resolve_voice.py                       # print which voice.json resolves
    python resolve_voice.py acmeco                # explicit client
    python resolve_voice.py --scaffold acmeco     # write a starter voice.json for a client
    python resolve_voice.py --validate path.json  # validate a voice.json against the schema
"""

from __future__ import annotations

import json
import os
import sys

# In-code last-resort neutral voice. Mirrors the schema every reader expects and carries
# NO brand identity or brand-specific rules -- the banned/preferred entries here are
# generic illustrative filler that a per-client guideline overwrites wholesale.
NEUTRAL_VOICE: dict = {
    "meta": {
        "version": "1.0.0",
        "generated": "",
        "generated_by": "brand-guideline",
        "sources": [],
    },
    "brand": {"name": "Your Brand", "one_liner": "", "audience": ""},
    "tone": {
        "attributes": ["clear", "direct", "confident"],
        "register": "professional",
        "person": "second-person",
        "sentence_length": "short-to-medium",
        "reading_level": "plain",
    },
    "do": [
        "Lead with the outcome or the answer.",
        "Use plain, concrete words the reader would say out loud.",
        "Prefer short sentences and active voice.",
    ],
    "dont": [
        "Do not hedge or pad with filler.",
        "Do not use jargon the audience would not use themselves.",
    ],
    "banned_terms": [
        {"term": "synergy", "reason": "corporate filler (placeholder)", "suggest": ""},
        {"term": "leverage", "reason": "jargon for a plain verb (placeholder)", "suggest": "use"},
    ],
    "preferred_terms": [
        {"instead_of": "utilize", "use": "use"},
        {"instead_of": "in order to", "use": "to"},
    ],
    "punctuation": {"oxford_comma": True, "exclamation_points": "avoid", "em_dash": "allowed"},
    "formatting": {"headings": "sentence case", "lists": "allowed", "contractions": "allowed"},
    "sign_off": "",
    "examples": [
        {
            "context": "opening line",
            "on_brand": "Your invoice is ready. The total is $1,200, due Friday.",
            "off_brand": "We are pleased to inform you that your invoice has now been generated.",
        }
    ],
}

# Top-level keys a conformant voice.json must carry. Kept small on purpose: the contract
# is the shape brand-police reads, not a rigid schema. Extra keys are allowed.
REQUIRED_KEYS = ("brand", "tone", "do", "dont", "banned_terms", "preferred_terms")


def find_vault_root(start: str | None = None) -> str:
    """Walk up until a dir contains BOTH 'agents' (or .claude/agents) and '.claude'.

    Copied verbatim in intent from resolve_brand.find_vault_root() so voice and visual
    tokens agree on where the vault is. Defaults to this file's own location so it works
    regardless of the caller's CWD.
    """
    d = os.path.abspath(start or __file__)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        if os.path.isdir(os.path.join(d, ".claude")) and (
            os.path.isdir(os.path.join(d, "agents"))
            or os.path.isdir(os.path.join(d, ".claude", "agents"))
        ):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(os.path.dirname(__file__))  # fell off the top; graceful
        d = parent


def active_client(explicit: str | None = None) -> str:
    """explicit arg -> env FORGE_ACTIVE_CLIENT -> default 'default'.

    Same precedence as resolve_brand.active_client() so a single env var switches BOTH
    the visual brand and the voice guideline to the same client at once.
    """
    if explicit:
        return explicit
    return os.environ.get("FORGE_ACTIVE_CLIENT") or "default"


def resolve_voice_path(client: str | None = None, start: str | None = None) -> str | None:
    """Return the first EXISTING voice source path, or None if only NEUTRAL_VOICE is available."""
    root = find_vault_root(start)
    who = active_client(client)
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(root, "clients", who, "brand", "voice.json"),
        os.path.join(root, ".claude", "voice.json.example"),
        os.path.join(here, "voice.json.example"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


def load_voice(client: str | None = None, start: str | None = None) -> tuple[dict, str]:
    """Resolve + load the active voice guideline as (dict, source_label).

    source_label is the resolved file path, or '<neutral>' when the in-code NEUTRAL_VOICE
    is used (no file on disk, or the file failed to parse).
    """
    path = resolve_voice_path(client, start)
    if path is None:
        return dict(NEUTRAL_VOICE), "<neutral>"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), path
    except (OSError, json.JSONDecodeError):
        return dict(NEUTRAL_VOICE), "<neutral>"


def validate_voice(voice: dict) -> list[str]:
    """Return a list of human-readable schema problems. Empty list == conformant.

    Intentionally lenient: it checks the contract brand-police depends on (the required
    top-level keys and the shape of the term lists), not every field. A guideline may
    carry extra keys freely.
    """
    errors: list[str] = []
    if not isinstance(voice, dict):
        return ["voice is not a JSON object"]
    for key in REQUIRED_KEYS:
        if key not in voice:
            errors.append(f"missing required key `{key}`")
    for list_key in ("do", "dont"):
        if list_key in voice and not isinstance(voice[list_key], list):
            errors.append(f"`{list_key}` must be a list of strings")
    for entry in voice.get("banned_terms", []) or []:
        if not isinstance(entry, dict) or "term" not in entry:
            errors.append("each banned_terms entry needs a `term` field")
            break
    for entry in voice.get("preferred_terms", []) or []:
        if not isinstance(entry, dict) or "instead_of" not in entry or "use" not in entry:
            errors.append("each preferred_terms entry needs `instead_of` and `use` fields")
            break
    return errors


def scaffold(client: str, start: str | None = None) -> str:
    """Write a starter voice.json for `client` from the neutral template. Returns the path.

    Never overwrites an existing file -- the guideline synthesis owns real content.
    """
    root = find_vault_root(start)
    dest_dir = os.path.join(root, "clients", client, "brand")
    dest = os.path.join(dest_dir, "voice.json")
    if os.path.isfile(dest):
        return dest  # already exists; caller decides whether to edit
    os.makedirs(dest_dir, exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(NEUTRAL_VOICE, f, ensure_ascii=True, indent=2)
        f.write("\n")
    return dest


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--validate":
        if len(args) < 2:
            print("usage: resolve_voice.py --validate <path.json>")
            sys.exit(2)
        try:
            with open(args[1], "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"cannot read {args[1]}: {e}")
            sys.exit(1)
        errs = validate_voice(data)
        if errs:
            print(f"INVALID -- {len(errs)} problem(s):")
            for e in errs:
                print("  - " + e)
            sys.exit(1)
        print("VALID -- conforms to the voice contract.")
        sys.exit(0)
    if args and args[0] == "--scaffold":
        if len(args) < 2:
            print("usage: resolve_voice.py --scaffold <client>")
            sys.exit(2)
        p = scaffold(args[1])
        print(f"scaffolded starter voice.json: {p}")
        sys.exit(0)
    client_arg = args[0] if args else None
    # Anchor the vault search at the operator's CWD, not __file__: a plugin-installed
    # copy lives under ~/.claude/plugins/... which has no vault-root ancestor, so a
    # __file__-anchored walk falls off the top and always resolves the shipped example.
    # Seeding at CWD walks UP to the real vault when the operator runs this from it.
    p = resolve_voice_path(client_arg, start=os.getcwd())
    who = active_client(client_arg)
    print(f"active_client = {who}")
    print(f"resolved      = {p if p else '<neutral> (in-code NEUTRAL_VOICE)'}")
