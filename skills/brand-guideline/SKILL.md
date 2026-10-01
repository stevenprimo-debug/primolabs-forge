---
name: brand-guideline
description: >
  Synthesize discovered brand materials into a per-client VOICE guideline -- the structured
  voice.json contract (tone attributes, DO and DON'T lists, banned and preferred term maps,
  punctuation and formatting rules, on-brand vs off-brand examples) plus a human-readable
  voice-guidelines companion. This is the artifact brand-police reads to enforce voice; brand.json
  holds visual tokens only, so voice needs its own file. Writes to clients/<client>/brand/voice.json
  resolved the brand-agnostic way (voice-resolver, never a hardcoded client path), and never ships
  a client's data -- only the neutral voice.json.example travels. Fire when the operator says "write
  our voice guide", "generate the voice guideline", "codify our tone", "turn this into a voice.json",
  or after brand-discover has gathered the source. Stage two of three: discover finds source,
  guideline writes voice.json, police enforces it. Distinct from brand-discover (that LOCATES
  material) and brand-police (that APPLIES the guideline). No preamble; the output is the written
  artifact path.
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
    Fire when the operator says: write our voice guide, generate the voice guideline, codify our
    tone, build the voice.json, turn this into a guideline -- OR automatically as stage two after
    brand-discover gathers the source material.
---

# Brand Guideline

## For future Claude (TL;DR -- read this first)

Stage two of the brand pipeline (**discover -> guideline -> police**). It turns the material
`brand-discover` found into one structured artifact: `clients/<client>/brand/voice.json`, the DATA
contract the other two skills share. The one rule: **voice.json is structured DATA, resolved
brand-agnostically** -- never hardcode `clients/<name>/...`; resolve the path through
`resolve_voice.py`, and never let a specific brand's rules leak into this skill (it is machinery;
the brand's bans and preferences are runtime data). Fill the schema from real evidence, write the
JSON, then emit a human-readable `voice-guidelines.md` companion beside it. Validate the JSON with
`resolve_voice.py --validate`. The common failure is writing a generic voice from thin air instead
of grounding every field in something `brand-discover` actually surfaced.

---

## Why this exists

`brand.json` is visual only -- palette, type, radius. Voice has nowhere to live, so without this
artifact "on-brand copy" means whatever the agent remembers, which drifts every session and cannot
be enforced. `voice.json` fixes that: one per-client file that names the tone, the DO and DON'T,
the banned and preferred words, and worked examples, in a shape a scanner can read. It is the spine
that makes `brand-police` deterministic instead of vibes.

It is DATA, not machinery, which is why it lives under `clients/<client>/brand/` (which never
ships) and is resolved the same way `brand.json` is -- by active client, through a resolver, never
by a baked path. The skill itself carries only the schema and a brand-neutral example. That
separation is the whole point: ship the machinery to every account, keep each brand's actual voice
private to that client's tree.

The structured JSON is the contract; the `voice-guidelines.md` companion is for humans who want to
read the guideline rather than parse it. Both come from the same synthesis pass so they never
disagree.

---

## The voice.json schema (the contract)

```
meta            { version, generated, generated_by, sources[] }
brand           { name, one_liner, audience }
tone            { attributes[], register, person, sentence_length, reading_level }
do              [ imperative strings -- what the voice DOES ]
dont            [ imperative strings -- what the voice AVOIDS ]
banned_terms    [ { term, reason, suggest } ]      # brand-police flags every hit
preferred_terms [ { instead_of, use } ]            # brand-police flags instead_of -> use
punctuation     { oxford_comma, exclamation_points, em_dash }
formatting      { headings, lists, contractions }
sign_off        string
examples        [ { context, on_brand, off_brand } ]
```

`banned_terms` and `preferred_terms` are the machine-enforceable core -- `brand-police/check.py`
reads exactly these two lists. Everything else guides the model's rewrite. Extra keys are allowed;
the required core is `brand, tone, do, dont, banned_terms, preferred_terms`. See
`voice.json.example` for a filled, brand-neutral sample.

---

## Step 1 -- Take the discovery handoff (or run it)

Start from `brand-discover`'s inventory and create-or-update verdict. If it has not run, run it
first -- do not synthesize a voice from memory. Confirm the active client so the resolver targets
the right tree (explicit arg, or env `FORGE_ACTIVE_CLIENT`).

## Step 2 -- Resolve the target path, brand-agnostically

Never hardcode a client path. Ask the resolver where this client's voice.json is (or would be):

```
python3 resolve_voice.py                 # print which voice.json resolves for the active client
python3 resolve_voice.py acme            # explicit client
python3 resolve_voice.py --scaffold acme # write a starter clients/acme/brand/voice.json (never overwrites)
```

If a real per-client `voice.json` already exists, you are UPDATING it -- read it first and preserve
what still holds. If only the `.example` resolves, you are creating fresh; `--scaffold` gives you a
starting file to fill.

## Step 3 -- Fill the schema from evidence, not invention

Populate each field from what discovery actually surfaced:

- **tone.attributes** -- three to five adjectives you can point to lines that prove.
- **do / dont** -- imperative, specific, testable. "Lead with the outcome" beats "be clear".
- **banned_terms** -- words the brand genuinely avoids, each with a reason and (where there is one)
  a suggested replacement. Leave empty rather than inventing bans.
- **preferred_terms** -- real swaps the brand makes (`instead_of` -> `use`).
- **examples** -- lift `on_brand` from real discovered copy; write the `off_brand` foil to contrast.

If the evidence is thin for a field, leave it minimal and say so -- an honest sparse guideline
beats a padded fictional one.

## Step 4 -- Write the JSON, then validate

Write the completed object to the resolved `clients/<client>/brand/voice.json` (ASCII, 2-space
indent). Then validate it against the contract:

```
python3 resolve_voice.py --validate clients/<client>/brand/voice.json
```

Fix any reported problem before moving on. A guideline that fails validation is not done --
`brand-police` depends on the required keys and the term-list shape being present.

## Step 5 -- Emit the human-readable companion

Write a `voice-guidelines.md` beside the JSON (same folder) that renders the same content for a
human reader: tone summary, the DO / DON'T lists, the banned and preferred tables, and the
examples. This is the copy a client or teammate reads; the JSON is what machines read. If the house
`md-to-branded-html` skill is available and the operator wants a branded read copy, hand the
markdown to it.

---

## Anti-patterns (refuse list)

- **Preamble.** First line of output is the written path or the verdict, not "Let me synthesize...".
- **Hardcoding a client path.** Always resolve through `resolve_voice.py`. A literal
  `clients/acme/...` in code or instructions is the failure this skill exists to prevent.
- **Inventing voice.** Every field traces to discovered evidence. No baking a house voice, no
  generic "professional yet approachable" filler, no inventing bans the brand never stated.
- **Baking brand data into the skill.** The skill ships the schema and a neutral example only. A
  specific brand's rules are runtime DATA under `clients/`, never in this repo.
- **Shipping client data.** `clients/` never ships. Only `voice.json.example` travels.
- **Skipping validation.** An unvalidated voice.json can silently break `brand-police`.

---

## Definition of done (universal)

Done means: a schema-conformant `voice.json` exists at the resolver-resolved
`clients/<client>/brand/voice.json`, every populated field traces to real discovered evidence
(not invention), `resolve_voice.py --validate` reports VALID, and a `voice-guidelines.md` companion
exists beside it. A voice.json that was not validated, or one whose fields were guessed, is not
done.

For brand-guideline specifically: the written `voice.json` path is stated, its validation result is
shown, and the human-readable companion path is named -- ready for `brand-police` to enforce.

---

- 2026-09-16 -- authored as stage two of the brand pipeline. voice.json is the shared structured
  contract (brand.json stays visual-only); resolved brand-agnostically via resolve_voice.py, with a
  neutral voice.json.example as the only shippable default.
