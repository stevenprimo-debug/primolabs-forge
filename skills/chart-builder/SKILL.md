---
name: chart-builder
description: >-
  Render Chart.js charts to PNG or standalone HTML from a JSON config. Wraps the same headless Chromium (Playwright) already vendored for html2pdf -- zero new deps -- plus a vendored Chart.js v4 bundle, so it works fully offline. Use this skill ANY time the operator asks to "make a chart", "plot this data", "chart this", "graph this", "render an equity curve", "draw a P&L chart", "P&L waterfall", "campaign funnel viz", "ranking trend chart", "dashboard chart", "visualize this CSV/JSON", or drops a dataset and wants a visualization. Supports all 8 native Chart.js types: line, bar, pie, doughnut, radar, polarArea, bubble, scatter, plus mixed (per-dataset type). Outputs a PNG by default (1200x600 @2x retina) or, with --emit-html, a self-contained HTML file that html2pdf swallows for proposal/scope/SOW/dashboard embedding. Wide net: any time data needs to become a picture, or a chart needs to land in a branded PDF, this skill should fire. Brand defaults (PrimoLabs burnt-orange palette + Outfit type) are applied automatically and are overridable per-config. The CLI lives at ${CLAUDE_PLUGIN_ROOT}/skills/chart-builder/chart_builder.py.
metadata:
  source: chartjs/Chart.js (MIT) vendored at vendor/chart.umd.min.js
  upstream: https://github.com/chartjs/Chart.js
  license: MIT (Chart.js) / Internal -- PRIMOLABS (wrapper)
---

# chart-builder

Renders [Chart.js](https://www.chartjs.org/) charts from a JSON config to a
**PNG** (default) or a **standalone self-contained HTML** file (`--emit-html`).
The render bridge is the same headless Chromium (Playwright) that `html2pdf`
already uses, so there are **zero new Python dependencies** — and the Chart.js
v4 bundle is vendored locally, so it works **fully offline** (no CDN).

## Why this exists

Five agents have load-bearing chart needs — equity curves, P&L bars, campaign
funnels, ranking trends, dashboard surfaces. Without a shared skill, each one
either reinvents the render bridge or skips charts. This is the universal-stack
fix: one CLI, vendored, offline-safe, branded by default.

It also pairs natively with **html2pdf**: a chart emitted as HTML
(`--emit-html`) flows straight into the seamless-PDF pipeline for proposals,
engineering scopes, SOWs, and dashboards.

## Quick start

```bash
# Default — render a JSON config to a PNG (1200x600 @2x retina)
python "${CLAUDE_PLUGIN_ROOT}/skills/chart-builder/chart_builder.py" \
    --config chart.json \
    --output equity_curve.png

# Custom dimensions / scale
python ".../chart_builder.py" --config chart.json -o out.png \
    --width 900 --height 500 --scale 2

# Emit-HTML mode — standalone self-contained HTML for html2pdf to swallow
python ".../chart_builder.py" --config chart.json --emit-html chart.html
python "${CLAUDE_PLUGIN_ROOT}/skills/html-to-pdf/html2pdf.py" chart.html
```

## Install (one-time)

Same as html2pdf — if html2pdf already works, this does too.

```bash
python -m pip install playwright
python -m playwright install chromium
```

## The JSON config

The config is passed **verbatim** to `new Chart(ctx, config)`. At minimum:

```json
{
  "type": "line",
  "data": {
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [{ "label": "Equity", "data": [10000, 10420, 11050] }]
  },
  "options": { "plugins": { "title": { "display": true, "text": "Equity Curve" } } }
}
```

- `type` — one of: `line`, `bar`, `pie`, `doughnut`, `radar`, `polarArea`,
  `bubble`, `scatter`, `mixed`. For `mixed`, omit the top-level `type` and set
  `type` on each dataset instead.
- `data` / `options` — the full Chart.js surface. Whatever you pass is fed
  straight through. The full options reference:
  https://www.chartjs.org/docs/latest/

## Brand defaults (auto-applied, overridable)

Before instantiation the template applies the PrimoLabs palette so charts
ship on-brand without per-config styling:

- Accent family: `#EA580C` (burnt orange) → `#F97316`, `#C2410C`, `#DC2626`
- Categorical series palette for multi-series / pie / doughnut slices
- Text `#15110d`, dim `#8A8278`, grid `rgba(21,17,13,0.10)`
- Font family Outfit (system-ui fallback)

Any color you set explicitly in the config wins — the defaults only fill gaps.

## Output modes

| Flag                 | Output                                  | Uses Chromium? | Use for                                                                               |
| -------------------- | --------------------------------------- | -------------- | ------------------------------------------------------------------------------------- |
| (default)            | PNG at `--width`x`--height` @`--scale`x | yes            | a chart image to drop into a doc, deck, or Discord                                    |
| `--emit-html <file>` | standalone self-contained HTML          | no             | embedding into a proposal/scope/SOW/dashboard that html2pdf renders to a seamless PDF |

`--emit-html` skips Chromium entirely — it just inlines the bundle + config
into the template and writes the file, so it is fast and CI-safe.

## Error handling

Chart.js and runtime errors are surfaced two ways:

1. The template captures them to `window.__CB_ERROR__` / `window.__CB_READY__`.
2. The renderer scrapes those off the page and re-emits to **stderr**, then
   exits non-zero. Page `console.error` output is also relayed to stderr.

So an invalid config fails loudly (non-zero exit + stderr message) instead of
producing a blank PNG.

## Fixtures / smoke tests

`tests/fixtures/` ships three generic configs (no real client data):

- `equity_curve.json` — line chart (FY equity)
- `pnl_bar.json` — grouped bar chart (quarterly P&L)
- `campaign_funnel.json` — doughnut (campaign funnel stages)

Smoke-test any of the 8 types by writing a config and rendering it.

## Consumer agents

Wired into the `skills:` block of: software-development, finance,
finance/specialists/fpa-forecasting, finance/specialists/investment-analyst,
marketing, seo-discoverability. (trading-analyst consumer archived in the
2026-07-21 roster flush — see `_archive/2026-07/roster-flush-2026-07-21/`.)

## Architecture notes

- Twin of `html-to-pdf` — same Playwright bootstrap, same vendoring discipline.
- `templates/chart_template.html` is the render scaffold; `chart_builder.py`
  inlines `vendor/chart.umd.min.js` (replacing `__CHARTJS_BUNDLE__`) and the
  JSON config (replacing `__CHART_CONFIG__`).
- PNG mode screenshots `#chart-wrap` (cropped tight), not the full page.
- Vendored Chart.js is pinned in `vendor/VERSION.txt`; re-vendor on major bumps.
