#!/usr/bin/env python3
"""PrimoLabs factory -- emits one agent or one skill, then validates.

A factory is a template plus a validator. This one emits ONE file and refuses to leave the
repo dirty.

    py -3 scripts/factory.py agent shopify   --desc "..." --docs https://shopify.dev/docs/api
    py -3 scripts/factory.py skill order-sync --desc "..." --docs https://shopify.dev/docs/api
    py -3 scripts/factory.py agent shopify   --desc "..." --dry-run

Refuses to overwrite. Runs the validator afterwards and reverts its own write if the repo
would be left failing -- so the factory cannot be the thing that introduces a finding.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# When run as a plugin the factory reads its own templates from the PLUGIN root and
# WRITES the emitted seat into the user's PROJECT repo -- never back into the plugin.
# Env vars are the official contract (code.claude.com/docs/en/plugins-reference);
# fall back to script-relative / cwd so a direct `py -3 scripts/factory.py` still works.
PLUGIN_ROOT = Path(
    os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent
).resolve()
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
TEMPLATES = PLUGIN_ROOT / "templates"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def die(msg: str) -> "None":
    print(f"factory: {msg}", file=sys.stderr)
    raise SystemExit(2)


def render(kind: str, slug: str, desc: str, docs: str) -> str:
    tpl = (TEMPLATES / f"{kind}.md").read_text(encoding="utf-8-sig")
    title = slug.replace("-", " ").title()
    out = (
        tpl.replace("{{SLUG}}", slug)
        .replace("{{TITLE}}", title)
        .replace("{{DESCRIPTION}}", desc)
        .replace("{{DOCS_URL}}", docs)
    )
    if not docs:
        # No vendor surface: drop the key rather than ship an empty one. Check 6 only
        # demands `docs:` when a third-party service is actually named. The value is
        # quoted in the template (`docs: "{{DOCS_URL}}"`) so prettier's YAML formatter
        # can't mangle the placeholder into `{ { DOCS_URL } }` -- so an empty substitution
        # leaves `docs: ""`, not `docs: `. Match both.
        #
        # SKILL: docs lives nested under metadata: per code.claude.com/docs/en/skills.
        # Drop the whole metadata block if its only child was an empty docs -- a bare
        # `metadata:` header with no children is malformed YAML and check 2 would fail.
        # AGENT: docs is top-level (subagent spec has no metadata field); drop just the
        # single line.
        if kind == "skill":
            out = re.sub(
                r'^metadata:\s*\n\s+docs:\s*(""|\'\')?\s*\n',
                "",
                out,
                flags=re.MULTILINE,
            )
        else:
            out = re.sub(r'^docs:\s*(""|\'\')?\s*\n', "", out, flags=re.MULTILINE)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["agent", "skill"])
    ap.add_argument("slug")
    ap.add_argument(
        "--desc",
        required=True,
        help="Router-rule description. Name concrete cases, not a topic.",
    )
    ap.add_argument(
        "--docs",
        default="",
        help="Canonical vendor docs URL. Required by Law 2 when the body "
        "names a third-party service.",
    )
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not SLUG_RE.match(a.slug):
        die(f"slug '{a.slug}' must be lowercase words joined by single hyphens")
    if len(a.desc) < 40:
        die("description is too vague to route on -- name concrete cases (check 8)")

    target = (
        PROJECT_DIR / ".claude" / "agents" / f"{a.slug}.md"
        if a.kind == "agent"
        else PROJECT_DIR / ".claude" / "skills" / a.slug / "SKILL.md"
    )
    if target.exists():
        die(
            f"{target.relative_to(PROJECT_DIR).as_posix()} already exists -- edit it, do not regenerate over it"
        )

    body = render(a.kind, a.slug, a.desc, a.docs)

    if a.dry_run:
        print(f"--- would write {target.relative_to(PROJECT_DIR).as_posix()} ---")
        print(body)
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8", newline="\n")
    print(f"wrote {target.relative_to(PROJECT_DIR).as_posix()}")

    # The factory validates its own output. If the repo would be left failing, the write
    # is reverted -- a generator that can dirty the tree is how debt accumulates.
    # validate.py resolves its scan root from CLAUDE_PROJECT_DIR, so point it at the
    # project we just wrote to (not the plugin) by passing that env through.
    val_env = dict(os.environ, CLAUDE_PROJECT_DIR=str(PROJECT_DIR))
    r = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "scripts" / "validate.py")],
        capture_output=True,
        text=True,
        env=val_env,
    )
    print(r.stdout.rstrip())
    if r.returncode != 0:
        target.unlink()
        if a.kind == "skill":
            try:
                target.parent.rmdir()
            except OSError:
                pass
        print(
            "\nfactory: validator failed -- write REVERTED. Fix the inputs and re-run.",
            file=sys.stderr,
        )
        return 1

    print(
        "\nNext: fill the {{...}} sections, declare skills: it always needs, and re-run "
        "scripts/validate.py"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
