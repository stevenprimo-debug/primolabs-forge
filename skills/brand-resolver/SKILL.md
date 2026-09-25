---
name: brand-resolver
description: Resolve the active brand.json by PROJECT, not by hardcoded path. Brand DATA is project-specific and lives in a per-project brand file that does not ship; the shippable tree carries only this resolver plus a neutral brand.json.example default. Any reader that needs brand tokens (renderers, index builders) calls resolve_brand_path() / load_brand() instead of hardcoding a path. Use when wiring a new brand-token reader, or when asked where the brand palette comes from.
user-invocable: false
metadata:
  type: skill
  ships_to_customer: true
---

# brand-resolver

One tiny helper: `resolve_brand.py`. It answers "which brand.json is active for the current project?" so no reader hardcodes a path to a specific brand's DATA.

## Why

Brand DATA is project-specific. A project's brand tokens live in a per-project brand file, which does not ship. The shippable tree may carry only brand MACHINERY plus a brand-neutral default (`.claude/brand.json.example`, and a copy bundled beside this resolver). A reader that hardcodes a path to one brand would (a) leak that path into the product and (b) break on a fork that has no such brand. This resolver removes the hardcode.

## API

```python
from resolve_brand import resolve_brand_path, load_brand
resolve_brand_path()            # active client = default -> path or None
resolve_brand_path("acmeco")    # explicit client
brand, src = load_brand()       # (dict, source_label)  -- src is the path or '<neutral>'
```

## Fallback chain (first that exists wins)

1. a per-project brand file resolved under the active slug — per-project brand (does not ship)
2. `<root>/.claude/brand.json.example` — generic neutral default (ships)
3. `skills/brand-resolver/brand.json.example` — neutral default bundled beside this resolver
4. in-code `NEUTRAL_BRAND` dict — last resort (always available, no file needed)

`active_client` precedence: **explicit arg → env `FORGE_ACTIVE_CLIENT` → default `"default"`.**

The root is derived by walking up to the dir containing BOTH `agents/` and `.claude/` (mirrors `md-to-branded-html/render.py`), so it holds across machines, moves, and forks. No hardcoded machine path.

## CLI (debug which file resolves)

```
python resolve_brand.py            # default client
python resolve_brand.py acmeco     # explicit client
```

## Callers

`md-to-branded-html/render.py` and other brand-token readers resolve through this helper. On a public install (no per-project brand tree) every one of them falls to the neutral `brand.json.example` with no crash.
