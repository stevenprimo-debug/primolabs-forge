# html-to-pdf

CLI: convert standalone HTML files to **seamless single-page PDFs** using
headless Chromium (Playwright). Works on any HTML — proposals, scopes,
reports, and landing pages.

Default mode is `--seamless`: one tall PDF page sized to the full content
height. No page breaks, no headers, no footers — the PDF reads like the
HTML scrolled top-to-bottom in a browser. Inspired by div riots'
html.to.design Figma plugin, which imports HTML into a single Figma frame.

A `--paginated` mode exists for cases that need traditional letter/A4
pages with page-number footers.

## Install

```bash
python -m pip install playwright
python -m playwright install chromium
```

The second command is mandatory — it pulls down ~110 MB of Chromium.

## Usage

```bash
# Default — seamless single-page PDF, output beside input as .pdf
python html2pdf.py input.html

# Custom output path
python html2pdf.py input.html -o out.pdf

# Batch — every *.html in the directory becomes a seamless .pdf
python html2pdf.py /path/to/folder/

# Paginated mode (opt-in)
python html2pdf.py input.html --paginated
python html2pdf.py input.html --paginated --format A4
python html2pdf.py input.html --paginated --margin 0.25in --landscape
python html2pdf.py input.html --paginated --no-headers

# Quiet (errors only)
python html2pdf.py input.html --quiet
```

`--help` for the full flag list.

## Modes

### `--seamless` (default)

| Setting                  | Value                                                 |
| ------------------------ | ----------------------------------------------------- |
| PDF pages                | 1                                                     |
| Page width               | content `scrollWidth` (matches HTML layout)           |
| Page height              | content `scrollHeight` (full document)                |
| Margins                  | 0                                                     |
| Headers/footers          | none                                                  |
| Print CSS                | OFF (`media="screen"`)                                |
| Background colors/images | preserved                                             |
| `vh` / `vw` units        | frozen to pixel values before snapshot                |
| Font load wait           | `networkidle` + `document.fonts.ready` + 400ms settle |
| Viewport                 | 850 × 1100 px (matches v5 `.page` max-width)          |

### `--paginated` (opt-in)

| Setting                  | Value                                             |
| ------------------------ | ------------------------------------------------- |
| Page size                | Letter (8.5 × 11 in), configurable via `--format` |
| Margins                  | 0.5 in all sides, configurable via `--margin`     |
| Orientation              | Portrait, `--landscape` to flip                   |
| Background colors/images | preserved                                         |
| Page-number footer       | on by default, `--no-headers` to disable          |
| Print CSS                | ON (`media="print"`)                              |
| Font load wait           | same as seamless                                  |
| Viewport                 | Set to page pixel dimensions                      |

## Output naming

- Single file, no `-o`: same path as input, `.html` → `.pdf`
- Single file, with `-o`: written to the explicit path
- Directory: every `*.html` writes alongside as `<name>.pdf`
  (`-o` ignored in batch mode, with a warning)

## Troubleshooting

### Fonts render as serif fallback

The HTML uses Google Fonts and the CDN didn't load in time.

1. Check internet connectivity.
2. If transient, re-run.
3. Bump the post-`fonts.ready` settle window: edit
   `wait_for_timeout(400)` in `_load_and_settle` to `1000` or higher.
4. Long-term: embed the font as base64 in the HTML or self-host.

### Cover page renders short or has white space below it

This is a paginated-mode-only issue. The `min-height: 100vh` cover is
keying off the print page height. Fix: drop `--paginated` and use the
default seamless mode (where `vh` is frozen before the PDF capture). Or
keep paginated and add `--margin 0` to honor the HTML's own
`@media print { @page { margin: 0 } }` rule.

### Seamless PDF page is enormous (e.g. 8.5" × 200")

Working as designed. Seamless mode produces a single page sized to the
full HTML content. If you need a traditional multi-page PDF, run with
`--paginated`.

### `networkidle` times out (60s)

The HTML references an external resource that never finishes loading.

1. Inline the external resource as base64 (preferred for portable
   v5-style proposals).
2. Edit `wait_until="networkidle"` in `_load_and_settle` to
   `wait_until="load"` — faster, may snapshot before fonts arrive.

### "Playwright is not installed"

Run both install lines:

```bash
python -m pip install playwright
python -m playwright install chromium
```

The second command is mandatory — `pip install` alone is not enough.

## File size

For a typical 19-section v5 proposal with base64-embedded images:

- Seamless: ~1.5–2 MB (one tall page)
- Paginated: ~2.5–3 MB (multi-page, more PDF overhead)

PDFs much larger than that usually mean the HTML has very high-res raster
images embedded — compress in the source HTML if size matters.

## Related skills

- `pdf` — read/edit/manipulate existing PDFs (different problem space)
- `docx` — Word docs
- `xlsx` — spreadsheets

This is the only CORE skill for HTML → PDF rendering.
