# md-to-branded-html

CLI: render a markdown working doc into a **branded, human-readable HTML** read copy,
using the active brand's palette + type system, resolved through the brand-resolver skill.

The rule it serves: nobody wants to read raw markdown. Any doc a HUMAN will sit and read
— a brief, architecture overview, strategy, proposal, status report, one-pager — gets a
branded HTML render. The markdown stays as the working source; this produces the read
copy. Machine-read docs (memory, handoffs, agent specs, raw internal diligence) stay
markdown and are never passed here.

Output styling comes entirely from `brand.json` (palette + fonts) — never hardcoded — so
every render carries one consistent brand and updates when the brand file does.

## Install

```bash
python -m pip install markdown
```

The `markdown` library powers the conversion (tables, fenced code, sane lists, attr_list, toc).

## Usage

```bash
# Render alongside the input as .html (title = first H1)
python render.py input.md

# Explicit output path + title + subtitle (the common case for a deliverable)
python render.py doc.md \
    -o doc.html \
    --title "Human Title" \
    --subtitle "One-line context"

# Point at a specific brand file
python render.py input.md --brand path/to/brand.json
```

`--help` for the full flag list.

## Flags

| Flag           | Effect                                                                                                                            |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `-o, --output` | Output `.html` path. Default: alongside input, `.md` → `.html`.                                                                   |
| `--title`      | Document title. Default: the doc's first H1 (which is then stripped from the body to avoid duplication under the styled title).   |
| `--subtitle`   | Optional one-line context rendered under the title.                                                                               |
| `--brand`      | Path to a `brand.json`. Default: resolve the active brand via the brand-resolver (per-project brand file → `.claude/brand.json.example` → neutral). |
| `--client`     | Active client slug for brand resolution. Default: `default`.                                                                     |

## Brand source of truth

Resolves the active `brand.json` through the brand-resolver:

| Token group                | Used for                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------ |
| `palette.*`                | backgrounds, text tiers, accent, borders, dividers, table fills, blockquote callouts |
| `typography.display_font`  | headings + wordmark (default Plus Jakarta Sans)                                      |
| `typography.body_font`     | body copy (default Inter)                                                            |
| `brand.name_stylized_html` | the wordmark in the header/footer                                                    |

No color or font is hardcoded — change the brand file, every render follows.

## Make a PDF

For a formal/print artifact, pipe the rendered HTML through the sibling skill
`html-to-pdf` (seamless = one tall non-paginated page):

```bash
python ../html-to-pdf/html2pdf.py doc.html
```

## Troubleshooting

### Tables or code blocks render as raw text

The markdown extensions did not load. Confirm `pip install markdown` succeeded; the script
enables `tables` + `fenced_code` explicitly. Re-run after install.

### Fonts render as a sans/serif fallback

The Google Fonts CDN didn't load. Check connectivity; transient failures resolve on re-run.
For a fully portable file, self-host or base64-embed the fonts in the template.

### Render carries the wrong brand

On a public install with no per-project brand tree, the renderer resolves the neutral
`.claude/brand.json.example`. To render against a specific brand, pass
`--brand <path/to/brand.json>` or set the active client with `--client <slug>`.

## Related skills

- `html-to-pdf` — convert finished HTML → seamless single-page PDF (the sibling; the next step)
- `pdf` — read/edit existing PDFs (different problem space)

This is the skill for markdown → branded HTML.
