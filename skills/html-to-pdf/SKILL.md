---
name: html-to-pdf
description: >
  Convert standalone HTML files to seamless single-page PDFs that match what Chrome renders — no page breaks, no pagination artifacts, no orphan headings. Default mode is `--seamless`: one tall PDF page sized to the full content height, inspired by div riots' html.to.design Figma plugin (https://html.to.design/) which imports HTML into a single Figma frame. Use this skill ANY time the user asks to "convert this HTML to PDF", "make a PDF of this proposal", "html2pdf", "render this scope as PDF", "turn this HTML into a PDF", "save this proposal as PDF", "export this engineering scope to PDF", "make these seamless", "no page breaks", "single-page PDF", or drops an .html file (with custom fonts, base64 images, and full-bleed cover pages) and wants a PDF version. Also trigger when Chrome's built-in print-to-PDF is breaking — viewport-unit covers (min-height: 100vh) not filling the page, Google Fonts falling back to serif, page breaks splitting headings from content. Paginated mode is available via --paginated for cases that need traditional letter/A4 pages. The CLI lives at ${CLAUDE_SKILL_DIR}/html2pdf.py and wraps headless Chromium via Playwright. Wide net: any time HTML and PDF are both mentioned in the same sentence, or any time a proposal/scope/SOW HTML needs to ship as a PDF, this skill should fire.
metadata:
  docs: https://playwright.dev/python/docs/api/class-page https://html.to.design/
---

# html-to-pdf

Wraps Playwright's headless Chromium to render standalone HTML files as
**seamless single-page PDFs**. Works on any HTML — proposals, scopes,
SOWs, reports, and landing pages with custom fonts, base64-embedded images,
and full-bleed cover pages.

## Why this exists

Chrome's built-in "Print to PDF" breaks on rich proposals because:

1. **`min-height: 100vh` covers** don't fill the page — Chrome uses the
   browser viewport, not the print page size, so the cover renders short.
2. **Google Fonts** (DM Sans) sometimes don't finish loading before the
   print snapshot, so headings render in the serif fallback.
3. **Page breaks** split headings from content, tables break mid-row, and
   the document looks horrid no matter how clean the HTML is.

This CLI fixes all three. Default behavior is **seamless**: one tall PDF
page sized to full content height, no page breaks at all — the PDF reads
like the HTML scrolled top-to-bottom in a browser. Inspired by div riots'
html.to.design Figma plugin, which imports HTML into a single Figma frame
the same way.

A `--paginated` mode exists for the rare case that letter/A4 pages with
page-number footers are required (e.g., a recipient who insists on
printing one page at a time).

## Quick start

```bash
# Default — seamless single-page PDF
python "${CLAUDE_SKILL_DIR}/html2pdf.py" \
    "MyProposal.html"

# Custom output path
python "${CLAUDE_SKILL_DIR}/html2pdf.py" input.html -o /path/to/output.pdf

# Batch mode — every *.html in the folder becomes a seamless PDF next to it
python "${CLAUDE_SKILL_DIR}/html2pdf.py" "Proposals/"

# Old-school paginated PDF (letter, page-number footer)
python "${CLAUDE_SKILL_DIR}/html2pdf.py" input.html --paginated

# Paginated, A4, no footer, tighter margins
python "${CLAUDE_SKILL_DIR}/html2pdf.py" input.html --paginated --format A4 \
    --no-headers --margin 0.25in
```

## Install (one-time)

```bash
python -m pip install playwright
python -m playwright install chromium
```

On a fresh machine, both lines are required — `pip install` only fetches the Python
wrapper, the second command pulls down ~110 MB of Chromium.

## Modes

### `--seamless` (DEFAULT)

One tall PDF page sized to full HTML content height. No page breaks, no
headers, no footers, no margins. The PDF is the HTML.

How it works:

1. Render at fixed 850 × 1100 px viewport (a common `.page` max-width
   and a Letter-ish height for `vh` resolution).
2. Wait for `networkidle` + `document.fonts.ready` + 400ms settle.
3. Walk the DOM and freeze any computed `vh`/`vw` heights to concrete
   pixel values — so resizing the PDF page to full content length doesn't
   make `min-height: 100vh` blow up the cover to the entire document.
4. Measure full content size (`scrollWidth` × `scrollHeight`).
5. `page.pdf()` with `width=<contentW>px height=<contentH>px margin=0`.

The result on a typical 19-section proposal: a single 8.86" × 148"
PDF page, ~1.5–2 MB. Opens in any PDF reader, scrolls top to bottom like
the original HTML.

### `--paginated`

Traditional multi-page PDF with letter/A4 pages and a page-number footer.
Use when a recipient explicitly needs to print individual pages.

| Flag           | Default  | Notes                                                                |
| -------------- | -------- | -------------------------------------------------------------------- |
| `--format`     | `Letter` | One of `Letter`, `A4`, `Legal`, `Tabloid`.                           |
| `--margin`     | `0.5in`  | Applied to all sides. Use `0` to honor the HTML's own `@page` rules. |
| `--landscape`  | off      | Rotate to landscape.                                                 |
| `--no-headers` | off      | Drop the page-number footer.                                         |

Footer template uses `<span class="title">` and
`<span class="pageNumber">` / `<span class="totalPages">` — these are
Chromium-native and auto-fill from the document.

## Paginated client PDF — older-client mode (EXCEPTION to seamless default)

**Seamless-non-paginated is and stays the DEFAULT** for screen/share docs
(briefs, status reports, dashboards-as-files, anything read on a device).
This section is the **named opt-in exception**, nothing more — it does not
change default behavior.

**When to use:** a traditional / older client who expects a normally-paginated,
contract-style PDF — discrete Letter/Legal pages they can print one at a time.
If the recipient is not that, use seamless.

**Command (Legal is the default for this mode):**

```bash
py -3 ${CLAUDE_SKILL_DIR}/html2pdf.py <in.html> \
    --paginated --format Legal -o <out.pdf>
```

`--format Letter` is also available. Prefer **Legal** — it tends to fit where
Letter spills a near-empty footer-only trailing page. (`--margin`, `--landscape`,
`--no-headers` from the paginated table above still apply.)

**Orphan-proof print CSS — the load-bearing fix.** In paginated mode Chromium
breaks pages wherever it likes: it strands a section heading at the bottom of a
page and splits a callout card across a page boundary. Add this `@media print`
block to the HTML to pin those break points. The reusable partial ships next to
this skill at `${CLAUDE_SKILL_DIR}/print-pagination.css` — paste it
in or `<link>` it, then **map the selectors to the target doc's actual
heading / lede / card classes** (the defaults match the depth-design-system
grammar emitted by md-to-branded-html):

```css
@media print {
  /* keep a section heading with its following content */
  .section-label,
  h2,
  h3 {
    break-after: avoid;
    page-break-after: avoid;
  }
  .section-lede {
    break-before: avoid;
    page-break-before: avoid;
  }
  /* never split a callout / check card across a page */
  .check,
  .card {
    break-inside: avoid;
    page-break-inside: avoid;
  }
}
```

**Ground:** keep the soft-grey `#F5F5F5` ground in print when the doc uses the
depth look (depth is shadow, not pure white) — do not force a white print background.

**Footer convention:** for a client-facing PDF, the HTML's own footer should carry a
**brand line** — e.g. `Your Brand · yourbrand.example`. **Never** ship a client-facing
PDF with a `Working document · rendered from markdown source` footer (that machine/working
footer is for internal reads only, never a client deliverable).

**Verify step (MANDATORY — do not skip).** After rendering, **READ the PDF**
and confirm all three: (1) no orphaned headings, (2) no card split across a
page, (3) no near-empty trailing page. If Letter spilled a footer-only last
page, re-render with `--format Legal`.

## Validation

Tested against a
`MyScope_v1.0.html`
(933 KB template, DM Sans, base64 images, full-bleed cover, 19 sections):

**Seamless (default):**

- 1 PDF page
- 8.86" × 148.47" (one continuous scroll)
- 1.8 MB
- Cover renders edge-to-edge with watermark and constellation graphics
- DM Sans loaded for all weights (400–800), no serif fallback
- All 19 sections flow continuously, no break artifacts anywhere
- Brand colors and gradients preserved

**Paginated (`--paginated`):**

- 19 pages, Letter, 0.5in margins, page-number footer
- 2.6 MB
- Available as fallback but not the default

## Common issues

**Cover renders short / `100vh` doesn't fill** — only happens in paginated
mode. Run with `--paginated --margin 0` to honor the HTML's own
`@page { margin: 0 }` rule. Or just use the default seamless mode where
this isn't a concern.

**Fonts rendering as serif** — Google Fonts CDN unreachable. Check
internet. If it's still happening on a stable connection, bump the
`wait_for_timeout(400)` line in `html2pdf.py` to 1000ms. Long-term:
embed the font as base64 in the HTML or self-host.

**`networkidle` timeout (60s)** — the HTML references something that
never finishes loading. Either inline the external resource as base64
(preferred for portable proposals) or change
`wait_until="networkidle"` to `wait_until="load"` in `_load_and_settle`.

**Seamless PDF feels too tall to scroll comfortably** — that's the point;
it's a continuous document. If a recipient needs paginated, run
`--paginated`. If they need both, run twice.

## Where it lives

- CLI: `${CLAUDE_SKILL_DIR}/html2pdf.py`
- README: `${CLAUDE_SKILL_DIR}/README.md`
- This skill: `${CLAUDE_SKILL_DIR}/SKILL.md`

## Future ideas (parking lot)

1. Local font caching / self-hosted font bundle so seamless mode
   works fully offline.
2. `--theme` flag for prebuilt seamless profiles (different default
   widths, e.g. 1200px for marketing pages vs 850px for proposals).
3. Concurrent batch rendering (currently serial).
4. `--png` / `--png-pdf` flag to output a single tall PNG image instead
   of a PDF (useful for embedding in decks or Notion).
5. Watermark injection (`--watermark "DRAFT"`) without modifying source
   HTML.
