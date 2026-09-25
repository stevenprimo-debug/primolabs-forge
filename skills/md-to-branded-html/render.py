#!/usr/bin/env python3
"""
md-to-branded-html -- Render a markdown working doc into a branded, human-readable
HTML page using the depth design system, with all brand TOKENS resolved from the
active brand.json via the shared brand-resolver.

Why this exists: nobody wants to read raw markdown. Any doc a HUMAN will sit and
read (briefs, architecture overviews, proposals) gets a branded HTML render. The
markdown stays as the working source; this produces the read copy.

The default output is a depth shell: monochrome ground #F5F5F5, near-black ink,
depth via the --pl-cascade + --pl-bevel-top shadow stack (depth IS the accent),
an orange spark #FF6A2B only on tiny round dots. Markdown maps onto the depth-
component grammar: H1 -> titleblock, H2 -> .section + .section-num +
.section-pill/.section-title, intro paragraph -> .section-lede, top-level bullet
lists -> .check cards, tables in the depth idiom.

Brand resolution: the depth-component CSS PATTERN (cascade/bevel/pill structure +
the component classes) is generic MACHINERY and lives in this template. The TOKEN
VALUES (--pl-* palette, font families, wordmark string) RESOLVE from the active
brand.json via the brand-resolver (default client "default"); when present, the
cascade/bevel shadow recipe is SLICED from the locked lockup's pl-lockup-css and
the lockup header is SLICED from the resolved style-pack. Nothing brand-specific is
inlined. On a public copy with no per-project brand tree, it falls back to the
neutral brand.json.example without crashing.

It does NOT decide WHICH docs to render -- that judgment ("will a human read
this?") is the caller's. Machine-read docs (memory, handoffs, agent specs,
internal diligence) stay markdown and are never passed here.

Usage:
    python render.py <input.md> [-o output.html] [--title "Doc Title"]
                     [--subtitle "..."] [--eyebrow "..."] [--pill "..."]
                     [--brand <path to brand.json>] [--client <client-slug>]

If -o is omitted, writes alongside the input with a .html extension (in the
current working directory when the input is there).
If --brand is omitted, the active brand.json is resolved via the brand-resolver
(per-project brand file -> .claude/brand.json.example -> in-code neutral).
--client defaults to "default". An explicit --brand path overrides the resolver.

Pair with the sibling core tool to make a single non-paginated PDF:
    python ../html-to-pdf/html2pdf.py <output.html>     (seamless is the default)

Requires: pip install markdown
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import sys

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency: pip install markdown")


def find_vault_root(start: str) -> str:
    """Walk up until a dir contains both 'agents' and '.claude' (the project root)."""
    d = os.path.abspath(start)
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
            return os.path.abspath(start)  # fell off the top; give up gracefully
        d = parent


def _load_resolver():
    """Load the sibling brand-resolver skill by path (it is hyphen-named, so a
    normal import won't reach it). Anchored on THIS file's location -- the
    resolver is a co-located sibling skill, always alongside this one, regardless
    of where the input markdown lives. Returns the module, or None if unavailable."""
    here = os.path.dirname(os.path.abspath(__file__))  # .../skills/md-to-branded-html
    resolver = os.path.join(os.path.dirname(here), "brand-resolver", "resolve_brand.py")
    if not os.path.isfile(resolver):
        return None
    spec = importlib.util.spec_from_file_location("resolve_brand", resolver)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _example_path() -> str:
    """Path to the shipped neutral default, anchored on this file's vault root."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = find_vault_root(here)
    return os.path.join(root, ".claude", "brand.json.example")


def load_brand(
    brand_path: str | None, input_path: str, client: str | None = None
) -> dict:
    # Explicit --brand path always wins (back-compat + manual override).
    if brand_path:
        with open(brand_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Otherwise resolve the active brand via the brand-resolver:
    #   per-project brand file -> .claude/brand.json.example -> neutral.
    resolver = _load_resolver()
    if resolver is not None:
        brand, _src = resolver.load_brand(client)
        return brand
    # Last-resort fallback if the resolver skill is somehow absent: the shipped
    # neutral default, then a hard error.
    example = _example_path()
    if os.path.isfile(example):
        with open(example, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(
        "No brand source found: brand-resolver skill missing and no "
        ".claude/brand.json.example present."
    )


def _slice_region(text: str, begin_pat: str, end_pat: str, label: str) -> str:
    """Return everything strictly between a BEGIN and END marker line."""
    b = re.search(begin_pat, text)
    e = re.search(end_pat, text)
    if not b or not e or e.start() <= b.end():
        raise RuntimeError(f"Could not slice '{label}' from lockup")
    return text[b.end() : e.start()].strip("\n")


def _resolve_lockup_path(brand: dict, client: str | None) -> str | None:
    """Resolve the active brand's locked-lockup file -- never a hardcoded path
    (resolve, don't embed).

    The brand portion resolves via the brand-resolver: we ask it for the active
    brand.json path and take its parent as the brand dir, so this honors
    explicit arg -> env FORGE_ACTIVE_CLIENT -> default 'default'. The lockup
    lives under <brand-dir>/style-packs/<pack>/lockup.html.

    Pack selection (the brand portion is always resolved; only the pack NAME defaults):
      1. an explicit brand['style_pack'] key, if the brand declares one;
      2. else, if exactly one style-pack dir exists, that one;
      3. else, the 'depth' default.

    Returns the lockup path if it exists, else None (a public copy with no
    per-project brand tree -> resolver returns the neutral .example, whose dir has
    no style-packs, so this returns None and the caller degrades to the plain
    wordmark)."""
    resolver = _load_resolver()
    brand_dir: str | None = None
    if resolver is not None:
        brand_json = resolver.resolve_brand_path(client)
        # Only a real per-project brand file carries a lockup; the neutral .example
        # ships without a style-packs/ tree.
        if brand_json and os.path.basename(os.path.dirname(brand_json)) == "brand":
            brand_dir = os.path.dirname(brand_json)
    if brand_dir is None:
        return None
    packs_dir = os.path.join(brand_dir, "style-packs")
    if not os.path.isdir(packs_dir):
        return None

    pack = brand.get("style_pack")
    if not pack:
        try:
            present = [
                d
                for d in os.listdir(packs_dir)
                if os.path.isdir(os.path.join(packs_dir, d))
            ]
        except OSError:
            present = []
        pack = present[0] if len(present) == 1 else "depth"

    lockup = os.path.join(packs_dir, pack, "lockup.html")
    return lockup if os.path.isfile(lockup) else None


def load_locked_lockup(
    brand: dict | None = None, client: str | None = None
) -> dict | None:
    """IMPORT the LOCKED brand lockup by slicing its delimited regions from the
    active brand's style-pack lockup.html (resolved via the brand-resolver --
    default client 'default'). Returns {'css','variant_a','variant_c'} or None if
    the lockup is absent (e.g. a public copy with no per-project brand tree) -- the
    caller then falls back to the plain wordmark header.

    The brand path is RESOLVED, never embedded. `brand` (the already-loaded brand
    dict) may declare a 'style_pack'; if omitted the pack defaults (single pack
    present, else 'depth').

    The 'css' region (pl-lockup-css) carries the --pl-cascade + --pl-bevel-top depth
    recipe AND the lockup component classes; the document template REUSES that depth
    recipe for its cards/pills so the shadow stack is INHERITED, never re-typed.
    The header is INHERITED byte-for-byte, never re-authored."""
    lockup = _resolve_lockup_path(brand or {}, client)
    if lockup is None or not os.path.isfile(lockup):
        return None
    try:
        with open(lockup, "r", encoding="utf-8") as f:
            src = f.read()
        css = _slice_region(
            src,
            r"<!--\s*=+\s*BEGIN pl-lockup-css.*?-->",
            r"<!--\s*=+\s*END pl-lockup-css.*?-->",
            "pl-lockup-css",
        )
        variant_a = _slice_region(
            src,
            r"<!--\s*=+\s*BEGIN variant-A.*?-->",
            r"<!--\s*=+\s*END variant-A.*?-->",
            "variant-A",
        )
        # variant-C = full header (lockup left + status pill right). We slice the
        # markup and re-point the pill text below.
        variant_c = _slice_region(
            src,
            r"<!--\s*=+\s*BEGIN variant-C.*?-->",
            r"<!--\s*=+\s*END variant-C.*?-->",
            "variant-C",
        )
        return {"css": css, "variant_a": variant_a, "variant_c": variant_c}
    except (OSError, RuntimeError):
        return None


def derive_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            return m.group(1).strip()
    return fallback


# --------------------------------------------------------------------------- #
# Markdown-HTML -> depth-component grammar                                     #
# --------------------------------------------------------------------------- #
#
# python-markdown gives us flat HTML (<h2>, <p>, <ul>, <table>, ...). The depth
# design system wants H2-delimited <section> blocks with a numbered .section-pill,
# a .section-lede intro, and top-level bullet lists rendered as .check depth cards.
# We transform the flat HTML into that grammar with a light, dependency-free pass.

_CHECK_TICK = (
    '<span class="tick"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"></polyline></svg></span>'
)


def _split_top_level_blocks(body_html: str) -> list[str]:
    """Split rendered markdown HTML into top-level sibling blocks (h2/h3/p/ul/...).

    python-markdown emits each block element flush-left on its own line region, so
    a regex that finds each opening top-level tag gives clean block boundaries. We
    only need to find <h2 ...> boundaries to group sections; everything between two
    H2s (or before the first) is that section's content, kept as-is.
    """
    # Find every top-level <h2 ...> ... </h2> and use its start as a section break.
    breaks = [m.start() for m in re.finditer(r"(?im)^<h2\b", body_html)]
    if not breaks:
        # No H2s: the whole body is one pre-section block. Return the SAME
        # (kind, chunk) tuple shape as the H2 path -- a bare string here made
        # to_depth_grammar's `for kind, chunk in chunks` unpack a string and
        # crash on any H2-less doc.
        return [("pre", body_html)] if body_html.strip() else []
    chunks = []
    pre = body_html[: breaks[0]].strip()
    if pre:
        chunks.append(("pre", pre))
    for i, b in enumerate(breaks):
        end = breaks[i + 1] if i + 1 < len(breaks) else len(body_html)
        chunks.append(("section", body_html[b:end].strip()))
    return chunks  # type: ignore[return-value]


def _checklistify(ul_html: str) -> str:
    """Convert a top-level <ul>...</ul> into a .checklist of .check cards.

    Each <li>...</li> becomes a depth card: a tick + the li's inner HTML as the body.
    Nested lists inside an li are preserved inside the card body. Ordered lists and
    nested lists are left untouched (only top-level <ul> become check cards)."""

    def _one(m: re.Match) -> str:
        inner = m.group(1)
        return (
            '<li class="check">'
            + _CHECK_TICK
            + '<span class="body">'
            + inner.strip()
            + "</span>"
            + "</li>"
        )

    items = re.sub(r"(?is)<li>(.*?)</li>", _one, ul_html)
    items = re.sub(r"(?i)^<ul>", '<ul class="checklist">', items, count=1)
    return items


def _style_section(section_html: str, num: int) -> str:
    """Wrap one H2-delimited chunk in the .section depth grammar.

    - The H2 becomes a .section-pill (numbered spark dot) + .section-title.
    - The first paragraph immediately after the H2 becomes the .section-lede.
    - The first top-level <ul> in the section becomes a .checklist of .check cards.
    """
    m = re.match(r"(?is)^<h2[^>]*>(.*?)</h2>(.*)$", section_html)
    if not m:
        return section_html
    title = m.group(1).strip()
    rest = m.group(2).strip()

    # Pull a leading <p> out as the lede (only the first, only if it leads).
    lede_html = ""
    lm = re.match(r"(?is)^<p>(.*?)</p>(.*)$", rest)
    if lm:
        lede_html = f'<p class="section-lede">{lm.group(1).strip()}</p>'
        rest = lm.group(2).strip()

    # Turn the FIRST top-level <ul> into a checklist of depth cards.
    rest = re.sub(
        r"(?is)<ul>(.*?)</ul>",
        lambda mm: _checklistify("<ul>" + mm.group(1) + "</ul>"),
        rest,
        count=1,
    )

    # The pill IS the section header — no section-num, no duplicate
    # h2.section-title. The h2 stays in the DOM for semantics/anchors but
    # visually hidden; the pill carries the visible title.
    return (
        '<section class="section">\n'
        '  <div class="section-label">\n'
        f'    <span class="section-pill"><span class="dot"></span>{title}</span>\n'
        "  </div>\n"
        f'  <h2 class="section-title sr-only">{title}</h2>\n'
        f"  {lede_html}\n"
        f"  {rest}\n"
        "</section>"
    )


def to_depth_grammar(body_html: str) -> str:
    """Transform flat markdown HTML into the depth-component grammar."""
    chunks = _split_top_level_blocks(body_html)
    if not chunks:
        return body_html
    out = []
    n = 0
    for kind, chunk in chunks:
        if kind == "section":
            n += 1
            out.append(_style_section(chunk, n))
        else:
            # Content before the first H2 (intro) — wrap as a lede-toned block.
            out.append(f'<div class="intro">{chunk}</div>')
    return "\n".join(out)


def build_template(
    body_html: str,
    title: str,
    subtitle: str,
    brand: dict,
    lockup: dict | None = None,
    eyebrow: str = "",
    pill: str = "",
    footer: str = "Working document &middot; rendered from markdown source.",
) -> str:
    b = brand.get("brand", {})
    typ = brand.get("typography", {})
    p = brand.get("palette", {})

    wordmark = (
        b.get("name_stylized_html")
        or b.get("name_stylized")
        or b.get("name", "YOUR BRAND")
    )
    pill_text = pill or (b.get("owner_dept_label") or "Internal Document")
    eyebrow_text = eyebrow or subtitle  # eyebrow defaults to subtitle context

    # Defaults = the depth design system. These fire only when brand.json omits a
    # key. Brand DATA still resolves from the active brand.json via the brand-
    # resolver; these in-code defaults are the fallback, not a hardcoded palette.
    display_font = typ.get("display_font", "Plus Jakarta Sans")
    body_font = typ.get("body_font", "Inter")
    fonts_href = typ.get(
        "google_fonts_href",
        "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap",
    )

    def g(k, d):
        return p.get(k, d)

    # The cascade/bevel depth recipe is the primary accent. We prefer to INHERIT it
    # from the sliced lockup CSS (which defines --pl-cascade / --pl-bevel-top);
    # these :root values are a fallback for when the lockup is absent (a public copy
    # with no per-project brand tree) so cards still carry depth.
    spark = g("accent", "#FF6A2B")
    css = f"""
    :root {{
      --bg-app: {g("bg_app", "#F5F5F5")};
      --card: {g("bg_card", "#F5F5F5")};
      --border: {g("border", "rgba(11,11,12,0.08)")};
      --divider: {g("divider", "rgba(11,11,12,0.08)")};
      --text: {g("text", "#0B0B0C")};
      --text-mid: {g("text_mid", "rgba(11,11,12,0.58)")};
      --text-dim: {g("text_dim", "rgba(11,11,12,0.30)")};
      --spark: {spark};
      --r-card: 20px;
      --r-panel: 40px;
    }}
    /* Depth recipe fallback — only used if the lockup CSS (which defines these) was
       not sliced in. The sliced pl-lockup-css overrides these with the locked
       6-layer cascade + white key-cap bevel. */
    :root {{
      --pl-cascade:
        0 0.71px 0.71px -0.67px rgba(0,0,0,0.08),
        0 1.81px 1.81px -1.33px rgba(0,0,0,0.08),
        0 3.62px 3.62px -2px    rgba(0,0,0,0.07),
        0 6.87px 6.87px -2.67px rgba(0,0,0,0.07),
        0 13.65px 13.65px -3.33px rgba(0,0,0,0.05),
        0 30px 30px -4px        rgba(0,0,0,0.02);
      --pl-bevel-top: inset 0 3px 1px 0 #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    html {{ -webkit-text-size-adjust: 100%; }}
    body {{
      background: var(--bg-app); color: var(--text);
      font-family: "{body_font}", "Inter Placeholder", system-ui, -apple-system, sans-serif;
      font-weight: 400; line-height: 1.62; font-size: 16px;
      -webkit-font-smoothing: antialiased;
    }}

    .wrap {{ max-width: 880px; margin: 0 auto; padding: 0 32px 96px; }}

    /* ---- title block ---- */
    .titleblock {{ padding: 64px 0 40px; border-bottom: 1px solid var(--divider); }}
    .eyebrow {{
      font-family: "{body_font}", sans-serif; font-size: 11px; font-weight: 500;
      letter-spacing: 0.2em; text-transform: uppercase; color: var(--text-dim); margin: 0 0 18px;
    }}
    .titleblock h1 {{
      font-family: "{display_font}", sans-serif; font-weight: 600;
      letter-spacing: -0.035em; line-height: 1.05; font-size: 42px; margin: 0 0 18px; color: var(--text);
    }}
    .titleblock .subtitle {{ font-size: 16px; color: var(--text-mid); margin: 0; line-height: 1.7; max-width: 62ch; }}
    .titleblock .subtitle strong {{ color: var(--text); font-weight: 600; }}

    /* ---- intro (content before first H2) ---- */
    .intro {{ padding: 36px 0 0; }}
    .intro > p {{ font-size: 16px; color: var(--text-mid); margin: 0 0 16px; max-width: 64ch; }}

    /* ---- section scaffolding ---- */
    .section {{ padding: 52px 0; border-bottom: 1px solid var(--divider); }}
    .section:last-of-type {{ border-bottom: none; }}
    .section-label {{ display: flex; align-items: center; gap: 14px; margin: 0 0 8px; flex-wrap: wrap; }}
    .section-num {{
      font-family: "{display_font}", sans-serif; font-weight: 600;
      font-size: 13px; letter-spacing: 0.04em; color: var(--text-dim);
    }}
    .section-pill {{
      display: inline-flex; align-items: center; gap: 9px;
      font-family: "{display_font}", sans-serif; font-size: 13px; font-weight: 600;
      letter-spacing: 0.16em; text-transform: uppercase; color: var(--text);
      background: var(--card); border-radius: 1000px; padding: 9px 18px;
      box-shadow: var(--pl-cascade), var(--pl-bevel-top);
    }}
    .section-pill .dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--spark); display: inline-block; flex-shrink: 0; }}
    h2.section-title {{
      font-family: "{display_font}", sans-serif; font-weight: 600;
      letter-spacing: -0.025em; font-size: 27px; line-height: 1.15; margin: 16px 0 0; color: var(--text);
    }}
    .sr-only {{
      position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0;
      overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
    }}
    .section-lede {{ font-size: 16px; color: var(--text-mid); margin: 14px 0 30px; max-width: 62ch; }}

    /* ---- body type ---- */
    h3 {{
      font-family: "{display_font}", sans-serif; font-weight: 600; font-size: 19px;
      letter-spacing: -0.02em; line-height: 1.25; margin: 32px 0 10px; color: var(--text);
    }}
    h4 {{
      font-family: "{display_font}", sans-serif; font-weight: 600; font-size: 15px;
      letter-spacing: 0.02em; margin: 26px 0 8px; color: var(--text-mid);
      text-transform: uppercase; letter-spacing: 0.08em;
    }}
    p {{ margin: 0 0 16px; color: var(--text-mid); line-height: 1.62; }}
    strong {{ color: var(--text); font-weight: 600; }}
    a {{ color: var(--text); text-decoration: none; border-bottom: 1px solid rgba(11,11,12,0.20); }}
    a:hover {{ border-bottom-color: var(--spark); }}

    /* plain (non-checklist) lists stay simple; spark only on the marker dot */
    ul, ol {{ margin: 0 0 18px; padding-left: 22px; color: var(--text-mid); }}
    li {{ margin: 7px 0; line-height: 1.6; }}
    ul:not(.checklist) li::marker {{ color: var(--spark); }}
    hr {{ border: 0; border-top: 1px solid var(--divider); margin: 40px 0; }}

    blockquote {{
      margin: 22px 0; padding: 18px 22px; background: var(--card); border-radius: var(--r-card);
      box-shadow: var(--pl-cascade), var(--pl-bevel-top); color: var(--text);
    }}
    blockquote p {{ color: var(--text); margin: 0; }}
    blockquote p + p {{ margin-top: 10px; }}

    /* code = depth card, Inter-toned (not a terminal); mono only inside <code> */
    code {{
      font-family: "{typ.get("mono_font", "ui-monospace")}", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.88em; background: rgba(11,11,12,0.04); padding: 2px 6px; border-radius: 6px; color: var(--text);
    }}
    pre {{
      background: var(--card); border-radius: var(--r-card); padding: 22px 24px;
      box-shadow: var(--pl-cascade), var(--pl-bevel-top); overflow-x: auto; margin: 0 0 22px;
      line-height: 1.7;
    }}
    pre code {{ background: none; padding: 0; color: var(--text); font-size: 13.5px; }}

    /* ---- delivered checklist (top-level bullets become depth cards) ---- */
    .checklist {{ list-style: none; margin: 0 0 8px; padding: 0; display: grid; gap: 14px; }}
    li.check {{
      background: var(--card); border-radius: var(--r-card); padding: 20px 22px;
      box-shadow: var(--pl-cascade), var(--pl-bevel-top);
      display: grid; grid-template-columns: 26px 1fr; gap: 16px; align-items: start; margin: 0;
    }}
    li.check .tick {{
      width: 22px; height: 22px; border-radius: 7px; margin-top: 2px; flex-shrink: 0;
      background: var(--card); box-shadow: var(--pl-cascade), var(--pl-bevel-top);
      display: flex; align-items: center; justify-content: center;
    }}
    li.check .tick svg {{ width: 12px; height: 12px; display: block; color: var(--text); }}
    li.check .body {{ font-size: 15px; line-height: 1.6; color: var(--text-mid); }}
    li.check .body strong {{ color: var(--text); font-weight: 600; }}
    li.check .body p {{ margin: 0 0 8px; }}
    li.check .body p:last-child {{ margin: 0; }}

    /* ---- inline status pill (depth chip, round spark dot) ---- */
    .pill-live, .tag-live {{
      display: inline-flex; align-items: center; gap: 6px; vertical-align: middle;
      margin-left: 8px; font-family: "{body_font}", sans-serif; font-size: 10px; font-weight: 600;
      letter-spacing: 0.16em; text-transform: uppercase; color: var(--text);
      background: var(--card); border-radius: 1000px; padding: 4px 12px 4px 10px;
      box-shadow: var(--pl-cascade), var(--pl-bevel-top);
    }}
    .pill-live .dot, .tag-live .dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--spark); flex-shrink: 0; }}

    /* ---- tables — depth card idiom ---- */
    table {{
      width: 100%; border-collapse: separate; border-spacing: 0; margin: 0 0 24px; font-size: 14.5px;
      background: var(--card); border-radius: var(--r-card); overflow: hidden;
      box-shadow: var(--pl-cascade), var(--pl-bevel-top);
    }}
    thead th {{
      background: var(--card); color: var(--text); font-family: "{display_font}", sans-serif;
      font-weight: 600; letter-spacing: -0.01em; text-align: left; padding: 14px 16px;
      border-bottom: 1px solid var(--divider);
    }}
    tbody td {{ padding: 12px 16px; border-bottom: 1px solid var(--border); color: var(--text-mid); vertical-align: top; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    tbody td strong {{ color: var(--text); font-weight: 600; }}

    /* ---- footer ---- */
    .foot {{ padding: 44px 0 0; margin-top: 8px; border-top: 1px solid var(--divider); color: var(--text-dim); font-size: 12.5px; line-height: 1.7; }}
    .foot .pl-lockup {{ margin-bottom: 14px; }}

    @media (max-width: 620px) {{
      .titleblock h1 {{ font-size: 34px; }}
      .wrap {{ padding: 0 22px 72px; }}
    }}
    """

    eyebrow_html = (
        f'<p class="eyebrow">{html.escape(eyebrow_text)}</p>' if eyebrow_text else ""
    )
    subtitle_html = (
        f'<p class="subtitle">{html.escape(subtitle)}</p>'
        if (subtitle and subtitle != eyebrow_text)
        else ""
    )

    # IMPORT the LOCKED brand lockup as the brand header when available. We slice
    # the FULL variant-C header (lockup left + status pill right) and re-point the
    # pill text. The lockup CSS (pl-lockup-css) ALSO carries the --pl-cascade /
    # --pl-bevel-top depth recipe the document cards reuse — so the depth stack is
    # inherited from the locked source, never re-typed. On a public copy with no
    # per-project brand tree the lockup is None and we fall back to a plain
    # wordmark header.
    if lockup:
        lockup_css = lockup["css"]
        header_src = lockup.get("variant_c") or lockup.get("variant_a") or ""
        # Re-point the pill text in the sliced variant-C header (the pill is the
        # only client/context-specific string in the markup).
        header_inner = re.sub(
            r'(?is)(<span class="pl-pill"><span class="dot"></span>).*?(</span>)',
            lambda m: m.group(1) + html.escape(pill_text) + m.group(2),
            header_src,
            count=1,
        )
        if "pl-header" in header_inner:
            header_html = header_inner
        else:
            # variant-A fell through (no pl-header wrapper) — wrap it.
            header_html = (
                '<header class="pl-header">\n'
                f"  {header_inner}\n"
                f'  <span class="pl-pill"><span class="dot"></span>{html.escape(pill_text)}</span>\n'
                "</header>"
            )
        foot_lockup = lockup.get("variant_a") or ""
    else:
        lockup_css = ""
        header_html = (
            '<header class="brandbar" style="display:flex;align-items:center;'
            "justify-content:space-between;max-width:880px;margin:0 auto;"
            'padding:28px 32px;border-bottom:1px solid rgba(11,11,12,0.08)">\n'
            f"  <span style=\"font-family:'{display_font}',sans-serif;font-weight:600;"
            f'letter-spacing:-0.02em;font-size:20px;color:var(--text)">{wordmark}</span>\n'
            f'  <span style="font-size:11px;letter-spacing:0.16em;text-transform:uppercase;'
            f'color:var(--text-dim)">{html.escape(pill_text)}</span>\n'
            "</header>"
        )
        foot_lockup = ""

    if foot_lockup:
        foot_brand = f'<span class="pl-lockup pl-sm">{foot_lockup}</span>'
    else:
        foot_brand = f"<span style=\"font-family:'{display_font}',sans-serif;font-weight:600;color:var(--text-mid)\">{wordmark}</span>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts_href}" rel="stylesheet">
{lockup_css}
<style>{css}</style>
</head>
<body>
{header_html}
<div class="wrap">

  <div class="titleblock">
    {eyebrow_html}
    <h1>{html.escape(title)}</h1>
    {subtitle_html}
  </div>

  {body_html}

  <div class="foot">
    {foot_brand}
    <div>{footer}</div>
  </div>

</div>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Render a markdown doc to branded HTML (depth design system)."
    )
    ap.add_argument("input", help="path to the .md file")
    ap.add_argument(
        "-o", "--output", help="output .html path (default: alongside input)"
    )
    ap.add_argument("--title", help="document title (default: first H1 or filename)")
    ap.add_argument("--subtitle", default="", help="optional subtitle under the title")
    ap.add_argument(
        "--eyebrow",
        default="",
        help="optional eyebrow label above the title (defaults to --subtitle context)",
    )
    ap.add_argument(
        "--pill",
        default="",
        help="status-pill text in the header (default: brand owner_dept_label)",
    )
    ap.add_argument(
        "--footer",
        default="Working document &middot; rendered from markdown source.",
        help="footer text below the brand lockup (raw HTML entities allowed). For a "
        "deliverable, e.g. 'Prepared for <name> &middot; <firm> &middot; <month year>'.",
    )
    ap.add_argument(
        "--brand", help="explicit path to brand.json (overrides --client resolution)"
    )
    ap.add_argument(
        "--client",
        default="default",
        help="active client slug for brand resolution (default: default). "
        "Resolves a per-project brand file -> "
        ".claude/brand.json.example -> neutral.",
    )
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        md_text = f.read()

    brand = load_brand(args.brand, args.input, args.client)
    title = args.title or derive_title(
        md_text, os.path.splitext(os.path.basename(args.input))[0]
    )

    # Strip a leading top-level H1 (it becomes the styled doc title) to avoid duplication.
    md_body = re.sub(r"^\s*#\s+.*\n", "", md_text, count=1)

    flat_html = markdown.markdown(
        md_body,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc"],
        output_format="html5",
    )

    # Map flat markdown HTML onto the depth-component grammar.
    body_html = to_depth_grammar(flat_html)

    lockup = load_locked_lockup(brand, args.client)
    page = build_template(
        body_html,
        title,
        args.subtitle,
        brand,
        lockup,
        eyebrow=args.eyebrow,
        pill=args.pill,
        footer=args.footer,
    )

    out = args.output or os.path.splitext(args.input)[0] + ".html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Rendered -> {out}")


if __name__ == "__main__":
    main()
