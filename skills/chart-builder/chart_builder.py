#!/usr/bin/env python3
"""chart-builder - Render Chart.js charts to PNG or standalone HTML from a JSON config.

Twin of html2pdf.py: wraps the same Playwright headless Chromium (zero new
deps). A JSON config is injected into chart_template.html with the vendored
Chart.js v4 bundle, then either screenshotted off the canvas to a PNG
(default) or written verbatim as a self-contained HTML file (--emit-html)
that html2pdf can swallow. Emitted HTML inlines bundle + config = offline.

Supports all 8 native Chart.js types: line, bar, pie, doughnut, radar,
polarArea, bubble, scatter (plus mixed via per-dataset type).
"""

from __future__ import annotations
import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print(
        "[chart-builder] ERROR: Playwright is not installed.\n"
        "    Run: python -m pip install playwright\n"
        "    Then: python -m playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(2)

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "chart_template.html"
BUNDLE_PATH = SKILL_DIR / "vendor" / "chart.umd.min.js"
SUPPORTED_TYPES = {
    "line",
    "bar",
    "pie",
    "doughnut",
    "radar",
    "polarArea",
    "bubble",
    "scatter",
    "mixed",
}
DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_SCALE = 1200, 600, 2

# Sentinel tokens replaced in chart_template.html at build time.
BUNDLE_TOKEN = "__CHARTJS_BUNDLE__"
CONFIG_TOKEN = "__CHART_CONFIG__"


@dataclass
class Options:
    config_path: Path
    output_path: Path | None
    emit_html_path: Path | None
    width: int
    height: int
    scale: int
    quiet: bool


def parse_args(argv: list[str] | None = None) -> Options:
    p = argparse.ArgumentParser(
        prog="chart-builder",
        description=(
            "Render a Chart.js chart from a JSON config to a PNG (default) "
            "or a standalone self-contained HTML file (--emit-html) that "
            "html2pdf can swallow. Offline-safe: the vendored Chart.js v4 "
            "bundle is inlined into the output."
        ),
    )
    p.add_argument(
        "--config",
        required=True,
        help=(
            "Path to a JSON file containing a Chart.js config object "
            '(at minimum {"type": ..., "data": {...}}). Passed through '
            "verbatim to new Chart(ctx, config)."
        ),
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output PNG path. Default: same path as --config with a .png "
            "extension. Ignored when --emit-html is given."
        ),
    )
    p.add_argument(
        "--emit-html",
        dest="emit_html",
        default=None,
        help=(
            "Instead of a PNG, write a standalone self-contained HTML file "
            "to this path (bundle + config inlined). Feed it to html2pdf "
            "for proposal/scope/SOW embedding. Skips Chromium entirely."
        ),
    )
    p.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help=f"Chart width in CSS px. Default: {DEFAULT_WIDTH}.",
    )
    p.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help=f"Chart height in CSS px. Default: {DEFAULT_HEIGHT}.",
    )
    p.add_argument(
        "--scale",
        type=int,
        default=DEFAULT_SCALE,
        help=f"Device scale factor for the PNG (retina). Default: {DEFAULT_SCALE}x.",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output (errors still printed).",
    )

    ns = p.parse_args(argv)
    config_path = Path(ns.config).resolve()

    output_path: Path | None = None
    if ns.output:
        output_path = Path(ns.output).resolve()

    emit_html_path: Path | None = None
    if ns.emit_html:
        emit_html_path = Path(ns.emit_html).resolve()

    return Options(
        config_path=config_path,
        output_path=output_path,
        emit_html_path=emit_html_path,
        width=ns.width,
        height=ns.height,
        scale=ns.scale,
        quiet=ns.quiet,
    )


def load_config(config_path: Path) -> dict:
    """Read + validate the Chart.js JSON config."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}") from e

    if not isinstance(cfg, dict):
        raise ValueError(
            f"Config must be a JSON object (got {type(cfg).__name__}): {config_path}"
        )
    ctype = cfg.get("type")
    if ctype is None:
        # Mixed charts can omit a top-level type (per-dataset type instead),
        # but for the wide-net case we still want a clear error otherwise.
        datasets = (cfg.get("data") or {}).get("datasets") or []
        if not any(isinstance(ds, dict) and ds.get("type") for ds in datasets):
            raise ValueError(
                'Config is missing a "type" key and no dataset specifies one. '
                f"Expected one of: {', '.join(sorted(SUPPORTED_TYPES))}."
            )
    elif ctype not in SUPPORTED_TYPES:
        raise ValueError(
            f'Unsupported chart type "{ctype}". '
            f"Expected one of: {', '.join(sorted(SUPPORTED_TYPES))}."
        )
    return cfg


def build_html(cfg: dict, width: int, height: int) -> str:
    """Inline the vendored bundle + JSON config into the template.

    The wrapper is sized to width x height (plus the template's padding) so
    the screenshot crops tight. Returns a fully self-contained HTML string.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")
    if not BUNDLE_PATH.exists():
        raise FileNotFoundError(f"Vendored Chart.js bundle not found: {BUNDLE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    bundle = BUNDLE_PATH.read_text(encoding="utf-8")
    config_json = json.dumps(cfg, ensure_ascii=False)

    # Order matters: inject the config first (it may itself contain the
    # literal token "__CHARTJS_BUNDLE__" only by accident — guard by doing
    # config last would risk the bundle text containing CONFIG_TOKEN, which
    # it does not). Bundle is huge; use plain str.replace (count=1) so we
    # never re-scan the injected bundle for the config token.
    html = template.replace(BUNDLE_TOKEN, bundle, 1)
    html = html.replace(CONFIG_TOKEN, config_json, 1)

    # Pin the wrapper size from the requested dimensions. The template's
    # #chart-wrap has 24px padding baked in; size the wrapper to content +
    # padding so the canvas itself gets width x height. With
    # responsive:false (set in-template so the screenshot captures a stable
    # final frame), Chart.js does NOT auto-size to the container — it uses
    # the canvas element's own width/height. So we must size the canvas
    # explicitly to width x height, both as drawing-buffer attributes and
    # as CSS, otherwise it falls back to Chart.js's 300x150-ish default and
    # the chart renders tiny in the top-left of the screenshot.
    pad = 24
    size_css = (
        f"#chart-wrap{{width:{width + pad * 2}px;height:{height + pad * 2}px;}}"
        f"#chart{{width:{width}px !important;height:{height}px !important;}}"
    )
    html = html.replace("</head>", f"<style>{size_css}</style></head>", 1)
    # Set the canvas drawing-buffer attributes (CSS px; Chart.js multiplies
    # by devicePixelRatio for the retina backing store automatically).
    html = html.replace(
        '<canvas id="chart"></canvas>',
        f'<canvas id="chart" width="{width}" height="{height}"></canvas>',
        1,
    )
    return html


async def _render_png(html: str, opts: Options) -> None:
    """Load the inlined HTML in headless Chromium, screenshot the wrapper."""
    out = opts.output_path or opts.config_path.with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            context = await browser.new_context(
                device_scale_factor=opts.scale,
                viewport={
                    "width": opts.width + 48 + 16,
                    "height": opts.height + 48 + 16,
                },
            )
            page = await context.new_page()

            # Surface page console errors to stderr as well.
            page.on(
                "console",
                lambda msg: (
                    print(
                        f"[chart-builder] console.{msg.type}: {msg.text}",
                        file=sys.stderr,
                    )
                    if msg.type == "error"
                    else None
                ),
            )

            await page.set_content(html, wait_until="networkidle", timeout=60_000)
            try:
                await page.evaluate("document.fonts.ready")
            except Exception:
                pass
            # Animation is disabled in-template; a short settle is plenty.
            await page.wait_for_timeout(250)

            # Scrape any Chart.js / runtime error the page captured.
            err = await page.evaluate("window.__CB_ERROR__ || null")
            ready = await page.evaluate("window.__CB_READY__ === true")
            if err:
                raise RuntimeError(f"Chart.js render error: {err}")
            if not ready:
                raise RuntimeError(
                    "Chart did not instantiate (window.__CB_READY__ never set). "
                    "Check the config's type/data shape."
                )

            wrap = page.locator("#chart-wrap")
            await wrap.screenshot(path=str(out))
        finally:
            await browser.close()

    if not opts.quiet:
        size_kb = out.stat().st_size / 1024
        print(
            f"[chart-builder] Wrote PNG: {out}  "
            f"({opts.width}x{opts.height} @{opts.scale}x, {size_kb:,.0f} KB)"
        )


def size_html(html: str) -> int:
    """Byte length of the emitted HTML (utf-8) — used for the emit summary."""
    return len(html.encode("utf-8"))


def emit_html(html: str, opts: Options) -> None:
    """Write the self-contained HTML to disk (no Chromium needed)."""
    out = opts.emit_html_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    if not opts.quiet:
        size_kb = size_html(html) / 1024
        print(f"[chart-builder] Wrote HTML: {out}  ({size_kb:,.0f} KB, self-contained)")


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse_args(argv)
        cfg = load_config(opts.config_path)
        html = build_html(cfg, opts.width, opts.height)
    except (FileNotFoundError, ValueError) as e:
        print(f"[chart-builder] ERROR: {e}", file=sys.stderr)
        return 1

    if opts.emit_html_path is not None:
        # --emit-html short-circuits the Chromium render entirely.
        emit_html(html, opts)
        return 0

    try:
        asyncio.run(_render_png(html, opts))
    except Exception as e:
        print(f"[chart-builder] FAILED: {e}", file=sys.stderr)
        return 1

    if not opts.quiet:
        print("[chart-builder] DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
