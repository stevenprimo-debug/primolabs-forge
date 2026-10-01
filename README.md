# PrimoLabs Forge

**A studio authoring kit for Claude Code and Cowork — v0.6.0.**

The tools a studio uses to build *with* Claude, packaged as one plugin: factories that
scaffold and validate skills, agents, and prompts; adversarial reasoning and pre-mortem
discipline; a brand voice pipeline; Chart.js charting; a branded Markdown → HTML/PDF
renderer; and cross-session recall.

All skills are PrimoLabs-authored and MIT-licensed. `the-fool` is a faithful, attributed port
of [jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) (MIT).

---

## Install

**Claude Code**

```bash
claude plugin marketplace add stevenprimo-debug/primolabs-forge
claude plugin install primolabs-forge@primolabs-forge
```

Skills invoke as `primolabs-forge:<skill>` (or the bare `/<skill>` when unambiguous).

**Cowork**

Install the `primolabs-forge.plugin` file: open it, browse the preview, and press **Accept**.
Cowork loads the skills; invoke them by describing the task or by name.

---

## What's inside — 14 skills

Versions marked `—` ship with the plugin (v0.6.0) and carry no independent version.

### Authoring — build the thing that builds

| Skill | What it does | How to use | Version |
|-------|--------------|-----------|---------|
| `skill-factory` | Interviews you, grounds in the live skills doc, then authors one skill — triggering description, body against the standard, references, an eval set, and a validation run. | "build a skill", "make a skill for X" | — |
| `agent-factory` | Authors one subagent seat — a focused, tool-restricted agent for isolated or parallel work. | "build an agent", "make a subagent for X" | — |
| `prompt-factory` | Builds a model-targeted structured prompt, splicing in per-model constraints. | "build a prompt", "author a system prompt" | — |
| `prompt-builder` | Turns a rough ask into a clean, structured XML prompt. | "turn this into a proper prompt" | — |

### Reasoning & discipline — catch the mistake before it costs you

| Skill | What it does | How to use | Version |
|-------|--------------|-----------|---------|
| `the-fool` | Structured adversarial reasoning in five modes (Socratic, dialectic, pre-mortem, red team, evidence audit) — steelmans first, then the 3–5 strongest challenges, then a strengthened synthesis. | "play devil's advocate", "red team this", "poke holes in this" | — |
| `pre-mortem` | Imagine the failure before it happens (Klein's technique) — surface failure modes and mitigations before you ship. | "run a pre-mortem", "what could go wrong" | — |

### Brand voice pipeline — discover → write → enforce

| Skill | What it does | How to use | Version |
|-------|--------------|-----------|---------|
| `brand-discover` | Gathers raw voice signal (samples, do/don'ts, references) into the inputs the guideline is built from. | "discover our brand voice", "start a voice guideline" | 1.0.0 |
| `brand-guideline` | Synthesizes the discovery into a structured `voice.json` (tone, do/don't, banned/preferred terms, examples). | "write our voice guideline" | 1.0.0 |
| `brand-police` | Validates copy against the active `voice.json`, flags every violation with line/column, then rewrites to match. | "is this on-brand", "voice-check this", "rewrite in our tone" | 1.0.0 |

### Rendering & data viz — make it readable

| Skill | What it does | How to use | Version |
|-------|--------------|-----------|---------|
| `md-to-branded-html` | Renders a Markdown working doc into a branded, human-readable HTML page using tokens from a per-project brand file. | "render this to branded HTML", "make the deliverable" | 1.0.0 |
| `html-to-pdf` | Converts an HTML page into a single seamless (non-paginated) PDF via headless Chromium. | "convert this HTML to PDF", "single-page PDF" | — |
| `chart-builder` | Renders Chart.js charts to PNG or standalone HTML from a JSON config. Chart.js is vendored — nothing to install for HTML output. | "make a chart", "plot this data", "chart this CSV/JSON" | — |
| `brand-resolver` | Resolves the active brand tokens by project with a neutral default, so renders never crash when no brand is configured. | (used by the renderers; "where does the brand come from") | — |

### Memory — carry context across sessions

| Skill | What it does | How to use | Version |
|-------|--------------|-----------|---------|
| `recall` | Maintains a plain `RECALL.md` in the project folder — reads the latest entries to catch you up, appends a dated entry to save state. Pure files; works in Cowork where the native memory has no skill API. | "catch me up", "where did we leave off", "save this to recall" | 1.0.0 |

---

## Prerequisites

The factory, reasoning, brand voice, and recall skills are pure Markdown/Python-stdlib and
need nothing. The rendering and charting skills call Python tools:

```bash
pip install playwright markdown
playwright install chromium
```

- `playwright` — headless Chromium for `html-to-pdf`, `chart-builder` PNG output, and PDF
  output from `md-to-branded-html`. `chart-builder` HTML output needs nothing (Chart.js is vendored).
- `markdown` — Markdown → HTML for `md-to-branded-html`.

Scripts invoke as `python3`; paths resolve via `${CLAUDE_PLUGIN_ROOT}`, so the kit is
portable across macOS, Linux, and Windows.

## Configure your brand (optional)

The renderers and the brand voice pipeline run with neutral defaults out of the box. To brand
them, set `FORGE_ACTIVE_CLIENT` and drop a `brand.json` / `voice.json` at the resolver's
per-project path (templates: `skills/brand-resolver/brand.json.example`,
`skills/brand-guideline/voice.json.example`). With nothing configured, everything falls back
to the bundled neutral palette and voice.

## License

MIT — see [LICENSE](./LICENSE). Authored by PrimoLabs ([primolabs.ai](https://primolabs.ai)).
