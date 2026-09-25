#!/usr/bin/env python3
"""
brand-resolver -- resolve the active brand.json by PROJECT, not by hardcoded path.

Why this exists: brand DATA is project-specific and lives in a per-project
brand file, which does not ship with the plugin.
The shippable tree carries only brand MACHINERY plus a brand-neutral default.
Readers (renderers, index builders) must NOT hardcode a path to a specific brand.json
-- they ask this resolver for the active brand file, and on a public install (no
per-project tree) it falls back to the bundled neutral brand.json.example, then to an
in-code neutral dict.

Fallback chain (first that exists wins):
  1. a per-project brand file (does not ship)          resolved under the active slug
  2. <root>/.claude/brand.json.example                 (generic neutral; ships)
  3. skills/brand-resolver/brand.json.example          (neutral default bundled beside this file)
  4. an in-code NEUTRAL_BRAND dict                      (last resort; always available)

active_client precedence:
  explicit arg  ->  env FORGE_ACTIVE_CLIENT  ->  default "default"

The root is derived by walking up to the dir containing BOTH agents/ and .claude/
(mirrors find_vault_root() in md-to-branded-html/render.py), so this holds across
machines, moves, and forks. No hardcoded machine path.

Stdlib only. Tiny by design -- no service, no state file.

Usage (library):
    from resolve_brand import resolve_brand_path, load_brand
    path = resolve_brand_path()                 # active client = default
    path = resolve_brand_path("acmeco")         # explicit client
    brand, src = load_brand("acmeco")           # (dict, "path or '<neutral>'")

Usage (CLI, for debugging which file resolves):
    python resolve_brand.py                      # prints resolved path for default client
    python resolve_brand.py acmeco               # prints resolved path for 'acmeco'
"""

from __future__ import annotations

import json
import os
import sys

# In-code last-resort neutral brand. Mirrors the flat schema every reader expects
# (brand / typography / palette / radius / depth). Carries NO project-specific
# identity. Kept in sync with brand.json.example in shape; this is the last-resort
# fallback when even the .example file is absent.
NEUTRAL_BRAND: dict = {
    "brand": {
        "name": "Your Brand",
        "name_stylized": "YOUR BRAND",
        "owner_dept_label": "TEAM",
    },
    "typography": {
        "display_font": "system-ui",
        "body_font": "system-ui",
        "mono_font": "ui-monospace",
        "google_fonts_href": "",
    },
    "palette": {
        "bg_app": "#ffffff",
        "bg_card": "#faf7f3",
        "bg_elev": "#faf7f3",
        "bg_inset": "#f1ede8",
        "border": "rgba(20,16,14,0.10)",
        "divider": "rgba(20,16,14,0.18)",
        "text": "#1a1310",
        "text_mid": "#5c5048",
        "text_dim": "#8a8278",
        "white_bevel": "#ffffff",
        "accent": "#2563eb",
        "accent_alt": "#475569",
    },
    "radius": {"btn": "10px", "card": "20px", "panel": "40px", "pill": "1000px"},
    "depth": {
        "sheen_graphite": "linear-gradient(180deg,#000 0%,#fff 170%)",
        "blur_glass": "5px",
    },
}


def find_vault_root(start: str | None = None) -> str:
    """Walk up until a dir contains BOTH 'agents' and '.claude' (the project root).

    Mirrors md-to-branded-html/render.py's find_vault_root(). Defaults to this
    file's own location so the resolver works no matter the caller's CWD.
    """
    d = os.path.abspath(start or __file__)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        # Accept agents at the root OR at .claude/agents (the layout Claude Code
        # loads from). Accept either, or the repo would resolve no root at all and
        # silently fall through to the neutral brand.
        if os.path.isdir(os.path.join(d, ".claude")) and (
            os.path.isdir(os.path.join(d, "agents"))
            or os.path.isdir(os.path.join(d, ".claude", "agents"))
        ):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(
                os.path.dirname(__file__)
            )  # fell off the top; graceful
        d = parent


def active_client(explicit: str | None = None) -> str:
    """explicit arg -> env FORGE_ACTIVE_CLIENT -> default 'default'."""
    if explicit:
        return explicit
    return os.environ.get("FORGE_ACTIVE_CLIENT") or "default"


def resolve_brand_path(
    client: str | None = None, start: str | None = None
) -> str | None:
    """Return the first EXISTING brand source path, or None if only the in-code
    NEUTRAL_BRAND dict is available.

    `client` follows the same precedence as active_client() (explicit -> env ->
    default 'default').

    Tier 1: a per-project brand file (does not ship), resolved under the active slug
    Tier 2: <root>/.claude/brand.json.example          generic neutral (ships)
    Tier 3: skills/brand-resolver/brand.json.example   neutral default beside this file
    Tier 4: None  -> caller uses NEUTRAL_BRAND

    Read as "the project's brand, else the neutral default, else nothing."
    """
    root = find_vault_root(start)
    who = active_client(client)
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(root, "clients", who, "brand", "brand.json"),
        os.path.join(root, ".claude", "brand.json.example"),
        # Neutral default that travels WITH this resolver (plugin install:
        # skills/brand-resolver/brand.json.example). Fires when no per-project or
        # repo tree exists, so a public copy renders neutral instead of falling to
        # the in-code dict.
        os.path.join(here, "brand.json.example"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


def load_brand(client: str | None = None, start: str | None = None) -> tuple[dict, str]:
    """Resolve + load the active brand as (dict, source_label).

    source_label is the resolved file path, or '<neutral>' when the in-code
    NEUTRAL_BRAND dict is used (no file on disk).
    """
    path = resolve_brand_path(client, start)
    if path is None:
        return dict(NEUTRAL_BRAND), "<neutral>"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), path
    except (OSError, json.JSONDecodeError):
        return dict(NEUTRAL_BRAND), "<neutral>"


if __name__ == "__main__":
    client_arg = sys.argv[1] if len(sys.argv) > 1 else None
    # Anchor the search at the current CWD, not __file__: a plugin-installed copy
    # lives outside any project tree, so a __file__-anchored walk falls off the top
    # and always resolves the bundled example. Seeding at CWD walks UP to the real
    # project root when run from inside it.
    p = resolve_brand_path(client_arg, start=os.getcwd())
    who = active_client(client_arg)
    print(f"active_client = {who}")
    print(f"resolved      = {p if p else '<neutral> (in-code NEUTRAL_BRAND)'}")
