#!/usr/bin/env python3
"""
html2pdf — Convert standalone HTML files to design-quality PDFs.

Designed for the generic proposal template family (DM Sans, base64-embedded
images, full-bleed cover pages, brand colors). Wraps Playwright's headless
Chromium so output matches what the HTML renders in Chrome — but with
controlled font loading and viewport sizing.

Two modes:

  --seamless (DEFAULT): single tall PDF page sized to the full content
    height. No page breaks, no headers, no footers. The PDF looks identical
    to scrolling the HTML in a browser. Inspired by div riots' html.to.design
    Figma plugin (https://html.to.design/) which imports HTML into a single
    Figma frame. Use this for proposals, scopes, and any v5-template doc.

  --paginated: traditional letter/A4 pagination with page-number footers.
    Use when the recipient needs to print pages individually or when the
    document was authored with explicit @page rules.

Usage:
    python html2pdf.py <input.html> [-o output.pdf]
    python html2pdf.py <input.html> --paginated [--format Letter|A4]
                                                [--margin 0.5in]
                                                [--no-headers] [--landscape]

If <input> is a directory, every *.html file inside is converted in place
(same name, .pdf extension).

Requires:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from playwright.async_api import async_playwright
except ImportError:
    print(
        "[html2pdf] ERROR: Playwright is not installed.\n"
        "    Run: python -m pip install playwright\n"
        "    Then: python -m playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(2)


# Letter at 96 CSS DPI: 8.5 x 11 in -> 816 x 1056 px
# A4 at 96 CSS DPI: 8.27 x 11.69 in -> 794 x 1123 px
PAGE_PIXELS = {
    "Letter": (816, 1056),
    "A4": (794, 1123),
    "Legal": (816, 1344),
    "Tabloid": (1056, 1632),
}

# Default viewport for seamless mode. Matches the proposal-Proposal v5
# .page max-width (850px) so the layout fills the PDF without gray gutters.
# vh units in the HTML resolve against the height (1100px) BEFORE the PDF
# is captured, so cover pages with `min-height: 100vh` get a concrete
# 1100px height and the layout doesn't blow up when we resize the page
# to the full content length.
SEAMLESS_VIEWPORT_W = 850
SEAMLESS_VIEWPORT_H = 1100

DEFAULT_FOOTER_TEMPLATE = (
    "<div style=\"font-family: 'DM Sans', Helvetica, Arial, sans-serif; "
    "font-size: 9px; color: #6E6F72; width: 100%; padding: 0 0.5in; "
    'box-sizing: border-box; display: flex; justify-content: space-between;">'
    '<span class="title"></span>'
    '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
    "</div>"
)

DEFAULT_HEADER_TEMPLATE = '<div style="display:none;"></div>'


@dataclass
class Options:
    input_path: Path
    output_path: Path | None
    seamless: bool
    page_format: str
    margin: str
    landscape: bool
    show_headers: bool
    quiet: bool


def parse_args(argv: list[str] | None = None) -> Options:
    p = argparse.ArgumentParser(
        prog="html2pdf",
        description=(
            "Convert standalone HTML files to design-quality PDFs via "
            "headless Chromium (Playwright). Default mode is --seamless: "
            "one tall page, no page breaks, matches what you see in browser."
        ),
    )
    p.add_argument(
        "input",
        help=(
            "Path to an .html file OR a directory containing .html files. "
            "Directories are processed in batch mode."
        ),
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output PDF path. Default: same path as input with .pdf "
            "extension. Ignored in batch (directory) mode."
        ),
    )

    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--seamless",
        dest="seamless",
        action="store_true",
        default=True,
        help=(
            "Default. Single tall PDF page sized to full content height. "
            "No page breaks, no headers, no footers."
        ),
    )
    mode.add_argument(
        "--paginated",
        dest="seamless",
        action="store_false",
        help=(
            "Traditional pagination with letter/A4 page size and "
            "page-number footers. Opt-in to override seamless default."
        ),
    )

    # Paginated-mode-only flags (silently ignored in seamless mode)
    p.add_argument(
        "--format",
        dest="page_format",
        default="Letter",
        choices=sorted(PAGE_PIXELS.keys()),
        help="[--paginated only] Page size. Default: Letter.",
    )
    p.add_argument(
        "--margin",
        default="0.5in",
        help=(
            "[--paginated only] Page margin applied to all sides "
            '(e.g. "0.5in", "12mm", "0"). Default: 0.5in.'
        ),
    )
    p.add_argument(
        "--landscape",
        action="store_true",
        help="[--paginated only] Render in landscape orientation.",
    )
    p.add_argument(
        "--no-headers",
        action="store_true",
        help="[--paginated only] Disable page-number footer.",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output (errors still printed).",
    )

    ns = p.parse_args(argv)
    input_path = Path(ns.input).resolve()

    output_path: Path | None = None
    if ns.output:
        output_path = Path(ns.output).resolve()

    return Options(
        input_path=input_path,
        output_path=output_path,
        seamless=ns.seamless,
        page_format=ns.page_format,
        margin=ns.margin,
        landscape=ns.landscape,
        show_headers=not ns.no_headers,
        quiet=ns.quiet,
    )


def discover_targets(
    input_path: Path, output_path: Path | None
) -> list[tuple[Path, Path]]:
    """Return list of (html_in, pdf_out) pairs to render."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if input_path.is_dir():
        if output_path is not None:
            print(
                "[html2pdf] WARNING: -o/--output is ignored in batch mode; "
                "each PDF is written next to its source HTML.",
                file=sys.stderr,
            )
        html_files = sorted(input_path.glob("*.html"))
        if not html_files:
            raise FileNotFoundError(f"No .html files found in directory: {input_path}")
        return [(html, html.with_suffix(".pdf")) for html in html_files]

    if input_path.suffix.lower() not in {".html", ".htm"}:
        raise ValueError(
            f"Input must be an .html/.htm file or a directory: {input_path}"
        )

    pdf_out = output_path if output_path is not None else input_path.with_suffix(".pdf")
    return [(input_path, pdf_out)]


async def _load_and_settle(page, html_path: Path) -> None:
    """Common load sequence: navigate, wait for fonts, give layout a beat."""
    file_url = html_path.resolve().as_uri()
    try:
        await page.goto(file_url, wait_until="networkidle", timeout=60_000)
    except Exception as e:
        raise RuntimeError(
            f"Failed to load {html_path}: {e}\n"
            "Hint: if the HTML references external fonts (Google Fonts), "
            "an internet connection is required."
        ) from e

    # Belt-and-suspenders: wait for document.fonts to actually finish parsing.
    try:
        await page.evaluate("document.fonts.ready")
    except Exception:
        pass

    # Tiny render settle window after fonts resolve.
    await page.wait_for_timeout(400)


async def render_seamless(
    page,
    html_path: Path,
    pdf_path: Path,
    opts: Options,
) -> None:
    """Render a single HTML file as ONE tall PDF page (no pagination)."""
    if not opts.quiet:
        print(f"[html2pdf] Rendering (seamless): {html_path}")

    # Set viewport before navigation so vh/vw units resolve against a
    # known, sane size BEFORE we measure or capture.
    await page.set_viewport_size(
        {
            "width": SEAMLESS_VIEWPORT_W,
            "height": SEAMLESS_VIEWPORT_H,
        }
    )

    # Use screen media so we get the browser look (not @media print rules
    # that hide nav, force pagination, etc.).
    await page.emulate_media(media="screen")

    await _load_and_settle(page, html_path)

    # Freeze viewport-relative heights to concrete pixels so resizing the
    # PDF page to the full content height doesn't make `min-height: 100vh`
    # blow the cover up to the entire document length.
    await page.evaluate(
        """() => {
            const vh = window.innerHeight;
            const vw = window.innerWidth;
            const walk = (root) => {
                root.querySelectorAll('*').forEach(el => {
                    const inline = el.getAttribute('style') || '';
                    if (/\\bv[hw]\\b/i.test(inline)) {
                        const cs = getComputedStyle(el);
                        ['minHeight','height','maxHeight','minWidth','width','maxWidth']
                            .forEach(p => {
                                const v = cs[p];
                                if (v && v.endsWith('px')) el.style[p] = v;
                            });
                    }
                });
            };
            walk(document);
            // Also handle stylesheet rules that use vh (e.g. .cover { min-height: 100vh })
            document.querySelectorAll('.cover, [class*="cover"], [class*="full-bleed"], [class*="hero"]').forEach(el => {
                const cs = getComputedStyle(el);
                ['minHeight','height'].forEach(p => {
                    const v = cs[p];
                    if (v && v.endsWith('px') && parseFloat(v) > 0) el.style[p] = v;
                });
            });
        }"""
    )

    # Re-measure after freezing — this is the canonical content size.
    metrics = await page.evaluate(
        """() => ({
            width: Math.max(
                document.documentElement.scrollWidth,
                document.body ? document.body.scrollWidth : 0
            ),
            height: Math.max(
                document.documentElement.scrollHeight,
                document.body ? document.body.scrollHeight : 0
            )
        })"""
    )
    content_w = max(int(metrics["width"]), SEAMLESS_VIEWPORT_W)
    content_h = max(int(metrics["height"]), SEAMLESS_VIEWPORT_H)

    # Resize viewport to match content so anything still keyed to viewport
    # (sticky elements, overflow clips) lays out cleanly for the snapshot.
    await page.set_viewport_size({"width": content_w, "height": content_h})
    await page.wait_for_timeout(150)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    await page.pdf(
        path=str(pdf_path),
        width=f"{content_w}px",
        height=f"{content_h}px",
        print_background=True,
        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        display_header_footer=False,
        prefer_css_page_size=False,
    )

    if not opts.quiet:
        size_kb = pdf_path.stat().st_size / 1024
        print(
            f"[html2pdf] Wrote:               {pdf_path}  "
            f"({content_w}x{content_h}px, {size_kb:,.0f} KB)"
        )


async def render_paginated(
    page,
    html_path: Path,
    pdf_path: Path,
    opts: Options,
) -> None:
    """Render a single HTML file as a multi-page PDF with letter/A4 pages."""
    if not opts.quiet:
        print(f"[html2pdf] Rendering (paginated): {html_path}")

    width_px, height_px = PAGE_PIXELS[opts.page_format]
    if opts.landscape:
        width_px, height_px = height_px, width_px
    await page.set_viewport_size({"width": width_px, "height": height_px})
    await page.emulate_media(media="print")

    await _load_and_settle(page, html_path)

    pdf_kwargs: dict = {
        "path": str(pdf_path),
        "format": opts.page_format,
        "print_background": True,
        "prefer_css_page_size": False,
        "landscape": opts.landscape,
        "margin": {
            "top": opts.margin,
            "right": opts.margin,
            "bottom": opts.margin,
            "left": opts.margin,
        },
    }

    if opts.show_headers:
        pdf_kwargs["display_header_footer"] = True
        pdf_kwargs["header_template"] = DEFAULT_HEADER_TEMPLATE
        pdf_kwargs["footer_template"] = DEFAULT_FOOTER_TEMPLATE
    else:
        pdf_kwargs["display_header_footer"] = False

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    await page.pdf(**pdf_kwargs)

    if not opts.quiet:
        size_kb = pdf_path.stat().st_size / 1024
        print(f"[html2pdf] Wrote:                 {pdf_path}  ({size_kb:,.0f} KB)")


async def render_one(page, html_in: Path, pdf_out: Path, opts: Options) -> None:
    if opts.seamless:
        await render_seamless(page, html_in, pdf_out, opts)
    else:
        await render_paginated(page, html_in, pdf_out, opts)


async def render_all(targets: Iterable[tuple[Path, Path]], opts: Options) -> int:
    failures = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            context = await browser.new_context()
            page = await context.new_page()
            for html_in, pdf_out in targets:
                try:
                    await render_one(page, html_in, pdf_out, opts)
                except Exception as e:
                    failures += 1
                    print(
                        f"[html2pdf] FAILED:    {html_in}\n           {e}",
                        file=sys.stderr,
                    )
        finally:
            await browser.close()
    return failures


def main(argv: list[str] | None = None) -> int:
    try:
        opts = parse_args(argv)
        targets = discover_targets(opts.input_path, opts.output_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"[html2pdf] ERROR: {e}", file=sys.stderr)
        return 1

    if not opts.quiet:
        n = len(targets)
        if opts.seamless:
            print(f"[html2pdf] {n} file(s) to render (seamless mode)")
        else:
            print(
                f"[html2pdf] {n} file(s) to render (paginated, "
                f"{opts.page_format}, margin={opts.margin}, "
                f"landscape={opts.landscape}, headers={opts.show_headers})"
            )

    failures = asyncio.run(render_all(targets, opts))
    if failures:
        print(
            f"[html2pdf] DONE with {failures} failure(s).",
            file=sys.stderr,
        )
        return 1

    if not opts.quiet:
        print("[html2pdf] DONE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
