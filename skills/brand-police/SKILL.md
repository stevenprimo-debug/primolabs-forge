---
name: brand-police
description: >
  Apply and enforce a client's voice guideline on a piece of copy -- validate that copy against the
  active voice.json, flag every banned term and preferred-term swap with line and column, then
  rewrite it to match the tone, DO and DON'T, punctuation, and formatting the guideline specifies.
  Reads clients/<client>/brand/voice.json resolved the brand-agnostic way (never a hardcoded client
  path); degrades to the neutral default on a shipped copy so it never crashes. Fire when the
  operator says "rewrite this in our tone", "make this sound like us", "this doesn't sound
  on-brand", "enforce our voice", "is this on-brand", "voice-check this", "brand-police this copy".
  Runs a deterministic scanner (check.py) for the enumerable violations, then a model pass for tone
  and structure the scanner cannot see. Stage three of three: discover finds source, guideline
  writes voice.json, police enforces it. Distinct from brand-guideline (that WRITES the guideline;
  this APPLIES it). No preamble; the first line of output is the verdict or the rewritten copy.
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
    Fire when the operator says: rewrite this in our tone, make this sound like us, this doesn't
    sound on-brand, enforce our voice, is this on-brand, voice-check this, brand-police this,
    on-brand check -- OR whenever copy is handed over to be brought into a client's voice.
---

# Brand Police

## For future Claude (TL;DR -- read this first)

Stage three of the brand pipeline (**discover -> guideline -> police**). It enforces the
`voice.json` that `brand-guideline` wrote. The one rule: **check mechanically first, then judge** --
run `check.py` to enumerate every banned term and preferred-term swap (line and column, repeatable,
complete), and only then apply model judgement for the things a scanner cannot see (tone,
structure, register, rhythm). Two modes: **validate** (report violations, change nothing) and
**apply** (rewrite the copy to conform, showing what changed and why). The voice.json is resolved
brand-agnostically through the sibling resolver -- never hardcode a client path, and on a shipped
copy with no client tree it degrades to the neutral default rather than failing. The common failure
is skimming for "obvious" problems and missing the enumerable ones the scanner would have caught
every time.

---

## Why this exists

"Make this sound like us" is unenforceable without a written voice, and unreliable even with one if
enforcement is a human (or a model) eyeballing the text. Banned words get missed, preferred swaps
get forgotten, and the same copy passes one day and fails the next. This skill splits enforcement
into the part a machine does perfectly -- enumerate the term-level violations -- and the part that
needs judgement -- tone and structure -- so the enumerable half is never the thing that slips.

It is the payoff of the other two skills: `brand-discover` gathers the source, `brand-guideline`
turns it into `voice.json`, and this skill spends that artifact on every piece of copy that has to
sound on-brand. Without it the guideline is a document nobody applies; with it the guideline is a
gate.

Like its siblings it carries no brand's rules itself. It resolves whichever client's `voice.json`
is active and enforces that. Ship it to every account; the voice it enforces is per-client data.

---

## Modes

- **validate** -- report every violation and a tone/structure assessment; change nothing. Use for
  "is this on-brand?" and for a pre-send gate.
- **apply** -- rewrite the copy to conform, then show what changed. Use for "rewrite this in our
  tone" / "make this sound like us".

---

## Step 1 -- Resolve the active voice and scan mechanically

Run the deterministic scanner against the copy (a file, or stdin):

```
python3 check.py <file>                 # human report, exit 1 on any violation
python3 check.py <file> --json          # machine-readable findings
python3 check.py --client acme <file>   # explicit client's voice
cat draft.md | python3 check.py -        # scan stdin
```

`check.py` resolves the active client's `voice.json` through the sibling resolver (brand-agnostic,
no hardcoded path) and flags every `banned_terms` hit and every `preferred_terms` swap with line
and column. It is stdlib-only and reads nothing over the network. This list is your floor -- it is
complete and repeatable for the enumerable rules, so start from it, never from a skim.

## Step 2 -- Judge what the scanner cannot see

The scanner catches words. It cannot judge tone, register, sentence rhythm, structure, or whether
the copy leads with the outcome. Read the `voice.json` `tone`, `do`, `dont`, `punctuation`,
`formatting`, and `examples`, then assess the copy against them. Name specific lines, not vibes:
"opens with a throat-clear instead of the outcome (DON'T #1)", not "feels a bit off".

## Step 3 -- Validate or apply

- **validate mode:** output the verdict -- the enumerated violations from `check.py` plus the
  tone/structure findings -- and stop. Change nothing.
- **apply mode:** rewrite the copy so every `check.py` finding is resolved and every tone/structure
  issue is fixed, staying faithful to the guideline's examples. Then show what changed: the
  before/after of each substantive edit and the guideline rule each one serves.

## Step 4 -- Re-scan after a rewrite

In apply mode, run `check.py` again on the rewritten copy. A rewrite is not done until the scanner
is clean -- if the rewrite introduced or missed a banned term, catch it now, not after it ships.
For high-stakes copy, an independent adversarial read (a fresh subagent given only the voice.json
and the rewrite) is worth the tokens; the deterministic re-scan is the minimum.

---

## Anti-patterns (refuse list)

- **Preamble.** First line is the verdict or the rewritten copy. Never "Let me check...".
- **Skimming past the scanner.** Always run `check.py`; never hand-eyeball the enumerable rules. The
  scanner exists because skims miss banned terms.
- **Hardcoding a client path.** The voice resolves through the sibling resolver by active client.
- **Silent rewriting.** In apply mode, show what changed and the rule each edit serves. A rewrite
  the operator cannot audit is not enforcement.
- **Skipping the re-scan.** A rewrite that was never re-scanned can ship a fresh violation.
- **Enforcing a house voice.** This skill enforces whatever `voice.json` is active. It carries no
  brand's rules of its own.

---

## Definition of done (universal)

Done means: `check.py` ran against the copy and its findings are shown; the tone/structure
assessment names specific lines against specific guideline rules; in apply mode the rewrite resolves
every finding, the changes are shown with the rule each serves, and a clean re-scan of the rewrite
is confirmed. A "looks on-brand to me" with no scanner run is not done.

For brand-police specifically: in validate mode, the verdict lists the enumerated violations plus
tone/structure findings; in apply mode, the rewritten copy is delivered with a change log and a
confirmed-clean `check.py` re-scan.

---

- 2026-09-16 -- authored as stage three of the brand pipeline. Enforces the per-client voice.json
  via a deterministic scanner (check.py) plus a model tone/structure pass; resolves the guideline
  brand-agnostically and degrades to the neutral default on a shipped copy.
