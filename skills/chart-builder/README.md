# chart-builder

Render [Chart.js](https://www.chartjs.org/) charts from a JSON config to a
**PNG** or a **standalone HTML** file — offline, on-brand, zero new deps.

Twin of `html-to-pdf`: same vendored Playwright Chromium. The Chart.js v4 UMD
bundle is vendored at `vendor/chart.umd.min.js`, so renders never touch a CDN.

## Install (one-time)

```bash
python -m pip install playwright
python -m playwright install chromium
```

(If `html-to-pdf` already works on this machine, so does this.)

## Usage

```bash
# PNG (default 1200x600 @2x retina)
python chart_builder.py --config chart.json --output chart.png

# Custom size + scale
python chart_builder.py --config chart.json -o chart.png \
    --width 900 --height 500 --scale 2

# Standalone HTML for html2pdf to swallow (no Chromium)
python chart_builder.py --config chart.json --emit-html chart.html
```

## Config

A JSON object passed verbatim to `new Chart(ctx, config)`:

```json
{
  "type": "bar",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [{ "label": "Revenue", "data": [42000, 51000, 47500, 63000] }]
  }
}
```

**Supported types:** `line`, `bar`, `pie`, `doughnut`, `radar`, `polarArea`,
`bubble`, `scatter`, `mixed` (per-dataset type).

**Brand defaults** (PrimoLabs burnt-orange palette + Outfit type) are
applied automatically and overridden by any colors you set in the config.

## Flags

| Flag                 | Default        | Meaning                                  |
| -------------------- | -------------- | ---------------------------------------- |
| `--config <json>`    | (required)     | Chart.js config JSON file                |
| `-o, --output <png>` | `<config>.png` | PNG output path                          |
| `--emit-html <file>` | —              | write self-contained HTML instead of PNG |
| `--width <px>`       | 1200           | chart width                              |
| `--height <px>`      | 600            | chart height                             |
| `--scale <n>`        | 2              | retina device scale factor (PNG only)    |
| `-q, --quiet`        | off            | suppress progress output                 |

## Errors

Invalid configs fail loudly — Chart.js / runtime errors are scraped off the
page and re-emitted to stderr with a non-zero exit. No silent blank PNGs.

## Fixtures

`tests/fixtures/` — generic smoke-test configs (no real client data):

- `equity_curve.json` (line)
- `pnl_bar.json` (grouped bar)
- `campaign_funnel.json` (doughnut)

```bash
python chart_builder.py --config tests/fixtures/equity_curve.json -o /tmp/eq.png
```

## Vendoring

Chart.js v4 (see `vendor/VERSION.txt`), MIT-licensed (`vendor/LICENSE.md`).
Re-vendor on major version bumps; update `VERSION.txt`.
