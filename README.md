# PrimoLabs Forge

An **authoring kit for Claude Code** — the tools a studio uses to build *with* Claude Code, packaged as a plugin. Factories that scaffold and validate skills, agents, and prompts; two discipline skills that catch mistakes before they cost you; and a branded Markdown → HTML/PDF renderer for the docs you hand to humans.

All skills are PrimoLabs-authored and MIT-licensed.

## Install

```bash
claude plugin marketplace add stevenprimo-debug/primolabs-forge
claude plugin install primolabs-forge@primolabs-forge
```

Or, in a session (Claude Code v2.1.275+):

```
/plugin install primolabs-forge --marketplace stevenprimo-debug/primolabs-forge
```

Skills invoke as `primolabs-forge:<skill>` (or the bare `/<skill>` when the name is unambiguous).

## What's inside

### Authoring — build the thing that builds
| Skill | What it does |
|-------|--------------|
| `skill-factory` | Author one skill: write the triggering description, structure the body against the skill-creator standard, split detail into references, add evals, validate. |
| `agent-factory` | Author one subagent seat — a focused, tool-restricted agent for isolated or parallel work. |
| `prompt-factory` | Build a model-targeted structured prompt, splicing in per-model constraints. |
| `prompt-builder` | Turn a rough ask into a clean, structured XML prompt. |

### Discipline — check before you commit
| Skill | What it does |
|-------|--------------|
| `pre-mortem` | Imagine the failure before it happens (Klein's technique) — surface failure modes and mitigations before you ship. |
| `deploy-reality-check` | Before any deploy or stack decision, confirm the *actual* live host/config/DNS against reality instead of trusting a doc. |

### Rendering — make it readable
| Skill | What it does |
|-------|--------------|
| `md-to-branded-html` | Render a Markdown working doc into a branded, human-readable HTML page using tokens from a per-project brand file. |
| `brand-resolver` | Resolve the active brand tokens by project, with a neutral default so renders never crash when no brand is configured. |
| `html-to-pdf` | Convert an HTML page into a single seamless (non-paginated) PDF. |

## Prerequisites

The factory and discipline skills are pure Markdown and need nothing. The rendering skills call Python tools:

```bash
pip install playwright markdown
playwright install chromium
```

- `playwright` — headless Chromium for `html-to-pdf` (and PDF output from `md-to-branded-html`)
- `markdown` — Markdown → HTML for `md-to-branded-html`

## Configure your brand (optional)

`md-to-branded-html` renders with neutral defaults out of the box. To brand it, copy `skills/brand-resolver/brand.json.example` to a `brand.json` and point the renderer at it with `--brand <path>`, or set `FORGE_ACTIVE_CLIENT` and drop a brand file at the resolver's per-project path. With no brand configured, it falls back to the bundled neutral palette.

## License

MIT — see [LICENSE](./LICENSE). Authored by PrimoLabs (primolabs.ai).
