---
name: brand-discover
description: >
  Discover a brand's source materials before writing anything in its voice -- inventory the
  LOCAL files that carry voice signal (existing brand tokens, a prior voice guideline, READMEs,
  about and positioning copy, marketing copy, shipped deliverables, prose docs) and note which
  optional connectors could enrich the pass. Connector-optional and local-first by design: it
  degrades gracefully to local files when document, wiki, design, chat, or transcript connectors
  are absent, and never hard-depends on any one integration. Fire at the START of any brand-voice
  job -- "learn our voice", "discover the brand", "what do we have to build a voice guide from",
  "onboard this client's brand", or before brand-guideline runs. Produces a discovery inventory
  grouped by signal strength plus the current voice.json state (create vs update). Stage one of
  three: brand-discover finds it, brand-guideline writes voice.json, brand-police enforces it.
  Distinct from brand-guideline -- this LOCATES source, it does not synthesize the guideline. No
  preamble; the first line of output is the inventory.
metadata:
  type: skill
  owner: core
  category: brand
  version: '1.0.0'
  status: operational
  voice: BALANCED
  source_path: none
  created_by: skill-factory
  ships_to_customer: true
  trigger: >
    Fire when the operator says: learn our voice, discover the brand, onboard this client's brand,
    what materials do we have, build a voice guide, find our brand source -- OR automatically as
    stage one before brand-guideline synthesizes a voice.json.
---

# Brand Discover

## For future Claude (TL;DR -- read this first)

Stage one of the three-skill brand pipeline (**discover -> guideline -> police**). Its job is
to find, not to synthesize: locate every LOCAL file that could teach this brand's voice, group
them by how strong a signal each carries, and report whether a `voice.json` already exists for the
active client. The one rule: **local-first, connector-optional** -- never fail because an
enterprise connector is missing; scan the files on disk and note connectors only as optional
enrichment. Run `discover.py` for the mechanical inventory, then read the strongest-signal files
yourself. Output is the inventory plus a create-or-update verdict for the guideline stage. The
common failure is treating a missing connector as a blocker instead of degrading to local files.

---

## Why this exists

Writing "in the brand's voice" without first gathering what the brand actually sounds like is how
an agent invents a voice and calls it the client's. The source almost always already exists --
scattered across a repo, a docs folder, old proposals, a landing page -- and the expensive mistake
is skipping the gather step and guessing. This skill makes the gather step cheap and repeatable.

It replaces a heavier connector-dependent discovery flow that required a stack of enterprise MCP
servers and fell over when any were absent. Ours inverts that: the local filesystem is the floor,
always available; connectors are a ceiling that raises the quality when present but is never
required. A customer who forks this plugin with nothing but a repo of markdown still gets a full
discovery pass.

The output feeds `brand-guideline`, which turns the discovered material into the per-client
`voice.json` contract. Getting discovery right -- finding the real source, not a stale README --
is what makes the guideline faithful instead of generic.

---

## Step 1 -- Run the local inventory

From the target repo or vault root:

```
python3 discover.py --json          # machine-readable, for feeding the next stage
python3 discover.py                 # human report
python3 discover.py --root <dir>    # scan an explicit tree
python3 discover.py --client acme   # report voice.json state for a specific client
```

`discover.py` walks the tree (skipping `.git`, `node_modules`, build output, `worktrees`, etc.),
classifies content files into signal buckets by name and location, and reports the active client's
current `voice.json` state. It is read-only and stdlib-only -- it lists paths; it does not open or
transmit file contents anywhere.

The signal buckets, strongest first:

- **voice-guideline** -- an existing `voice.json`, tone-of-voice doc, or style guide. If present,
  you are UPDATING, not starting cold.
- **brand-tokens** -- `brand.json` / brand-kit / brand-guidelines. Visual, but often carries the
  tagline, name styling, and positioning line.
- **about-positioning** -- about / mission / values / manifesto / messaging. The purest voice
  signal after an explicit guideline.
- **marketing-copy** -- landing pages, hero copy, taglines. Shows the voice in production.
- **deliverable** -- shipped proposals, case studies, one-pagers. Voice under real constraints.
- **readme / prose-doc** -- weakest signal; useful only if nothing better exists.

## Step 2 -- Read the strongest source, not all of it

The inventory ranks candidates; you still have to read. Open the top buckets first and stop when
you have enough distinct voice signal to characterize tone, vocabulary, and structure. Do not read
400 prose docs -- read the guideline (if any), the about/positioning copy, and two or three real
deliverables. Quote or note the specific phrasings that define the voice; those become the
guideline's examples.

## Step 3 -- Note optional connectors, never wait on them

If a document store, design source, chat history, or call/transcript connector is connected in
this session, name it as an available enrichment and pull the obviously-relevant material (a
messaging doc, a brand wiki page). If none are connected, say so in one line and proceed on local
files. Absence of a connector is never a reason to stop or to ask the operator to install one
mid-job -- surface it as a note, not a blocker.

## Step 4 -- Hand off with a create-or-update verdict

Close discovery by stating, in one line each: what the strongest sources are, whether `voice.json`
already exists for this client (so the next stage knows to create or update), and any signal gap
worth flagging (e.g. "no marketing copy on disk -- voice examples will lean on proposals"). That
verdict is the input `brand-guideline` needs.

---

## Anti-patterns (refuse list)

- **Preamble.** First line of output is the inventory or the verdict. Never "Let me look...".
- **Connector dependence.** Never fail, block, or nag because an enterprise connector is absent.
  Local files are the floor; connectors are optional ceiling.
- **Reading everything.** The inventory ranks so you can be selective. Reading every prose doc is
  waste, not thoroughness.
- **Inventing voice.** If the source is thin, say the source is thin. Do not fill the gap with a
  generic "professional and approachable" voice and present it as discovered.
- **Baking in brand data.** This skill is machinery. It discovers a specific brand's material at
  runtime; it carries no brand's rules, bans, or preferences itself.

---

## Definition of done (universal)

Done means: the local inventory ran and its output is shown, the strongest sources were actually
read (not just listed), the current `voice.json` state is stated (create vs update), optional
connectors are noted as present-or-absent in one line, and the create-or-update verdict for
`brand-guideline` is named. A list of file paths nobody opened is not discovery.

For brand-discover specifically: the discovery inventory exists in the transcript, grouped by
signal bucket, with a one-line handoff verdict naming the strongest sources and whether the
guideline stage creates or updates `clients/<client>/brand/voice.json`.

---

- 2026-09-16 -- authored as stage one of the brand pipeline (discover -> guideline -> police),
  replacing a connector-dependent discovery flow with a local-first, connector-optional one.
