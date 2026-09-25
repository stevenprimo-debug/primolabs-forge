#!/usr/bin/env python3
"""Refuse to let one client's token ride a shipped skill to another tenant.

    py -3 scripts/scan_tenant_tokens.py [<repo>] [--tokens FILE] [--staged]

Exit 0 = clean.  Exit 1 = a tenant token was found in a shipped file; do not push.
Exit 2 = git failed / bad repo.  Exit 3 = no token denylist configured.

WHY THIS EXISTS
    The plugin installs at account scope on your account AND on each client account.
    A client name, domain, or project number baked into a shipped file therefore rides to
    EVERY account that installs the plugin -- one tenant's data leaking onto another's
    surface. This gate is run before a push (see .githooks/pre-push) to catch that before
    it ships.

THE DENYLIST IS NEVER BAKED INTO THIS REPO -- that would itself be the leak. It resolves
local, in this order:
    1. --tokens FILE
    2. the path named in ~/.claude/tenant-tokens.path   (optional pointer --
       deliberately not written in any repo)
    3. the default ~/.claude/tenant-tokens.txt
    4. none found -> exit 3 and say so, rather than passing silently.

A token file is one token per line; blank lines and lines starting with '#' are ignored.
A token matches case-insensitively on a whole-word-ish boundary (not inside a longer word),
so "acme" hits "Acme" and "acme-corp" but not an unrelated substring.

CEILING (ponytail): matching is literal per-token -- domains, project numbers, and display
names only get caught if they are IN the token file, so keep it current. There is no
quotation carve-out: any appearance of a tenant token in a shipped file is treated as a leak.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TOKENS = Path.home() / ".claude" / "tenant-tokens.txt"
POINTER = Path.home() / ".claude" / "tenant-tokens.path"

# Never scanned: not shipped, binary, or the gate's own machinery.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".githooks"}
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mov", ".pyc",
}

# The leak surface is what INSTALLS on a client account. A plugin clones its WHOLE repo into
# the cache (~/.claude/plugins/cache/<mkt>/<plugin>/), and skills invoke
# ${CLAUDE_PLUGIN_ROOT}/scripts/*.py -- so scripts/ ships and CAN leak. The old allowlist
# (skills/hooks/commands/agents only) skipped scripts/ on a false "never ships" premise, and a
# real proj_<client> example rode through it undetected (found 2026-09-24). Scan every tracked
# text file except the maintainer-only surfaces in SKIP_DIRS and binaries. The scanner's own
# example tokens are synthetic (acme/globex/initech) so it does not self-trip.


def _read_list(path: Path) -> list[str]:
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(ln)
    return out


def load_tokens(explicit: str | None) -> tuple[list[str], str]:
    """Return (tokens, source description), or SystemExit(3) if unconfigured."""
    src: Path | None = None
    if explicit:
        src = Path(explicit).expanduser()
    elif POINTER.is_file():
        pointed = _read_list(POINTER)
        if pointed:
            src = Path(pointed[0]).expanduser()
    elif DEFAULT_TOKENS.is_file():
        src = DEFAULT_TOKENS

    if src is None:
        print(
            "NO TOKEN DENYLIST CONFIGURED.\n"
            f"  Create {DEFAULT_TOKENS} (one token per line),\n"
            f"  or set {POINTER} to point elsewhere, or pass --tokens FILE.\n"
            "  The list is never stored in this repo.",
            file=sys.stderr,
        )
        raise SystemExit(3)
    if not src.is_file():
        print(f"ERROR: token file not found: {src}", file=sys.stderr)
        raise SystemExit(3)
    tokens = _read_list(src)
    if not tokens:
        print(f"ERROR: token file is empty: {src}", file=sys.stderr)
        raise SystemExit(3)
    return tokens, str(src)


def build_patterns(tokens: list[str]) -> list[tuple[str, re.Pattern]]:
    return [
        (t, re.compile(r"(?<![0-9A-Za-z])" + re.escape(t) + r"(?![0-9A-Za-z])", re.IGNORECASE))
        for t in tokens
    ]


def find_hits(text: str, patterns: list[tuple[str, re.Pattern]]) -> list[tuple[int, str, str]]:
    """Pure core (testable): (lineno, token, line) for each token found in text."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for token, rx in patterns:
            if rx.search(line):
                hits.append((i, token, line.strip()))
    return hits


def tracked_files(repo: Path, staged: bool) -> list[str]:
    cmd = ["git", "-C", str(repo)] + (
        ["diff", "--cached", "--name-only"] if staged else ["ls-files"]
    )
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        print(f"ERROR: not a git repo, or git failed: {repo}", file=sys.stderr)
        raise SystemExit(2)
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def scannable(path: str) -> bool:
    p = path.replace("\\", "/")
    if any(seg in SKIP_DIRS for seg in p.split("/")):
        return False  # maintainer-only surfaces that never reach a client runtime
    return Path(p).suffix.lower() not in SKIP_SUFFIXES


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", default=".", help="path to the repo to scan")
    ap.add_argument("--tokens", help="local token denylist file")
    ap.add_argument("--staged", action="store_true", help="scan only staged changes")
    a = ap.parse_args()

    repo = Path(a.repo).expanduser().resolve()
    tokens, src = load_tokens(a.tokens)
    patterns = build_patterns(tokens)
    files = [f for f in tracked_files(repo, a.staged) if scannable(f)]

    findings: list[tuple[str, int, str, str]] = []
    for rel in files:
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: not a text leak surface
        for lineno, token, line in find_hits(text, patterns):
            findings.append((rel, lineno, token, line))

    print(f"tenant-token scan -- {repo}")
    print(f"  denylist: {len(tokens)} token(s) from {src}")
    print(f"  scanned:  {len(files)} file(s)")

    if not findings:
        print("\nCLEAN -- no tenant token in any shipped file.")
        return 0

    print(f"\nBLOCKED -- {len(findings)} tenant-token hit(s):\n")
    for rel, lineno, token, line in findings[:50]:
        print(f"  {rel}:{lineno}  [{token}]  {line[:100]}")
    if len(findings) > 50:
        print(f"  ... and {len(findings) - 50} more")
    print("\nA published plugin ships to every account that installs it.")
    print("Remove the tenant token (or resolve it at runtime) before pushing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
