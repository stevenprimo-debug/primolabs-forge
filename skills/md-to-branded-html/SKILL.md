---
name: md-to-branded-html
description: >
  Render a markdown working doc into a branded, human-readable HTML read copy using the
  active brand's palette, resolved through the brand-resolver. Fire whenever you write or deliver any
  markdown a HUMAN will sit and READ -- brief, architecture overview, strategy, proposal,
  status report, one-pager -- internal OR client-facing.
  Trigger phrases: "render this to HTML", "make an HTML version", "nobody wants to read markdown",
  "branded HTML", "create the deliverable". Produces a
  branded .html read copy; the markdown stays the working source. Do NOT
  fire for machine-read docs -- memory, handoffs, agent specs, raw diligence whose conclusion already
  lives in a read-doc. Pairs with the sibling skill html-to-pdf for a single non-paginated PDF, but
  is distinct from it (that converts finished HTML to PDF; this converts markdown to branded HTML).
  No preamble; the rendered file path is the output.
metadata:
  docs: https://fonts.googleapis.com/ https://fonts.gstatic.com/
  type: skill
  owner: core
  category: deliverables
  version: '1.0.0'
  status: operational
  voice: BALANCED
  source_path: none
  created_by: skill-factory
  trigger: >
    Fire when the user says: render this to HTML, make an HTML version, nobody wants to read
    markdown, branded HTML, create the deliverable -- OR automatically
    as the last step after writing any human-read working .md.
---

# Markdown to Branded HTML

## TL;DR -- read this first

Any markdown a HUMAN will read gets a branded HTML read copy; machine-only docs stay markdown. The discriminator is **audience, not document status**. Run `py -3 ${CLAUDE_SKILL_DIR}/render.py <input.md> -o <out.html>` -- it resolves the active brand's tokens via the shared brand-resolver (a per-project brand file -> `.claude/brand.json.example` -> in-code neutral; default client `default`) and emits the **depth look by default**: monochrome `#F5F5F5` ground, near-black ink, depth via the `--pl-cascade` + `--pl-bevel-top` shadow stack (depth IS the accent), an orange spark `#FF6A2B` only on tiny round dots, Plus Jakarta Sans display + Inter body. Markdown maps onto the depth grammar automatically -- H1 -> titleblock, H2 -> `.section` + `.section-num` + `.section-pill`/`.section-title`, intro paragraph -> `.section-lede`, top-level bullet lists -> `.check` depth cards, tables in the depth idiom -- and when a style-pack lockup exists it is SLICED into the header (flat-vector mark + wordmark + spark). If `-o` is omitted, output lands alongside the input (in the current working directory when the input is there); the markdown stays untouched as the working source. The one way this goes wrong: rendering a machine-read doc (memory, raw diligence) that nobody reads, or hand-authoring HTML instead of driving the script and the resolved `brand.json`. Optional flags: `--eyebrow` (label above title), `--pill` (header status-pill text, defaults to the brand's owner_dept_label).

---

## Why this exists

Markdown gives headers, bold, lists, and 240 lines that all look the same. Branded HTML carries hierarchy, color-coded sections, real tables, and shares anywhere as a link. Anyone evaluating work by reading it is taxed by raw markdown every time.

This skill wraps the working `render.py` so every agent producing a human-read doc renders it the same way against one brand source of truth, instead of each hand-authoring HTML and drifting.

The engine is the co-located `render.py`. This SKILL.md is the WHEN and the HOW; `render.py` is the mechanism. Do not reimplement the renderer in prose -- drive the script.

---

## Step 1 -- Apply the audience test (decide IF it renders)

Before rendering, ask: **will a human sit and READ this doc?**

- **Yes** -- brief, architecture overview, strategy, proposal, status report, one-pager (internal OR client-facing) -> render it.
- **No / machine-read only** -- memory, handoffs, agent specs, raw internal diligence whose conclusion already lives in a read-doc -> **markdown only, do NOT render.**

When unsure, default to render -- a wrongly-rendered doc costs nothing; a wrongly-skipped one taxes the reader.

## Step 2 -- Run the renderer

```bash
py -3 ${CLAUDE_SKILL_DIR}/render.py <input.md> \
    -o <name>.html \
    --title "Human Title" \
    --subtitle "One-line context (optional)"
```

- `--title` defaults to the doc's first H1 (the leading H1 is stripped from the body so it is not duplicated under the styled title).
- `--subtitle` is optional context under the title; `--eyebrow` is an optional label above the title; `--pill` sets the header status-pill text (defaults to the brand's `owner_dept_label`).
- `--brand`/`--client` are optional; omitted, the active brand resolves via the shared brand-resolver (a per-project brand file -> `.claude/brand.json.example` -> in-code neutral; `--client` defaults to `default`). An explicit `--brand <path>` overrides resolution. Paths resolve from the project root (nearest ancestor with `.claude/`, plus either `agents/` or `.claude/agents/`), never from cwd.
- Requires `pip install markdown` (tables / fenced_code / sane_lists / attr_list / toc extensions are enabled).

## Step 3 -- Place the output

Keep working-source markdown where the work lives; render the branded HTML as a separate read copy (default: alongside the input). Never overwrite the markdown source -- the render is a copy, the markdown stays the source of truth.

## Step 4 -- (optional) make a single non-paginated PDF

When the doc must be a formal/print artifact, pair with the sibling skill `html-to-pdf` -- seamless is the default (one tall page, no pagination):

```bash
py -3 ${CLAUDE_PLUGIN_ROOT}/skills/html-to-pdf/html2pdf.py <name>.html
```

## Step 5 -- QA + deliver

Confirm the render: tables/code/headings converted, no raw markdown leaked (no leading `|` table rows, no bare `##`), brand accent present.

---

## Anti-patterns (refuse list)

- **Preamble.** First line of output IS the rendered file path / verdict. Never "Let me render this for you."
- **Rendering machine-read docs.** Memory, handoffs, specs, raw diligence whose decision is already extracted stay markdown. Rendering them is noise.
- **Hand-authoring the HTML instead of driving the script.** The script + `brand.json` are the single source of truth for palette/type. Hand-rolled HTML drifts from brand.
- **Hardcoding colors/fonts.** All brand values resolve through the brand-resolver —
  `from resolve_brand import load_brand; brand, src = load_brand()` — which reads
  the active brand's `brand.json` and falls back to the neutral
  `.claude/brand.json.example`. Never inline a hex the resolved brand does not declare, and
  never hardcode a brand path -- brand DATA is project-specific and is resolved, not named.
- **Overwriting the markdown source.** The render is a read copy; the markdown stays the working source.

---

## Definition of done

Done means: the deliverable exists at a named path (or the verdict is stated outright), every factual claim in it was checked against the live system rather than assumed, and the next action is named.

For Markdown to Branded HTML specifically: the human-read doc opens as a branded, hierarchy-rich HTML page -- tables, code, and sections rendered, brand palette applied from `brand.json`, the markdown source untouched -- and nobody has to read raw markdown.

---
