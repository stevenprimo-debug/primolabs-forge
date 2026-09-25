---
name: deploy-reality-check
description: >
  Pre-deploy and pre-stack-decision reality check. Fire BEFORE any deploy, host change, DNS
  cutover, or platform pick whenever a canonical, default, or memory doc tells you where
  something lives ("we deploy to Vercel", "the site is on Y"). It confirms the ACTUAL live host,
  the real repo config, and DNS against reality instead of trusting the doc, then enforces
  precedence (a product's own deploy doc overrides the generic canonical default) and the
  reversibility gate (confirm target plus blast radius before executing). What goes wrong without
  it - an agent reads a stale default and deploys to the wrong platform, burning tokens on a
  hard-to-reverse mistake. Distinct-from neighbor - this is the INVOCABLE checklist you run on
  demand; the always-on inherited gate is a deploy-verify rule in your repo. Never uses preamble;
  the first line of output IS the verdict.
metadata:
  docs: https://developers.cloudflare.com/ + https://vercel.com/docs
  type: skill
  owner: software-development/devops-release
  category: devops
  version: '1.0.0'
  status: operational
  voice: BALANCED
  source_path: none
  created_by: skill-factory
  trigger: >
    Fire when the user says: deploy, ship it, push to prod, cut over, flip DNS, make this
    live, where does this deploy, is this on Vercel or Cloudflare, what stack is X on, before
    any deploy or platform decision that relies on a doc's claim about the host.
---

# Deploy Reality Check

## For future Claude (TL;DR -- read this first)

Before you act on ANY deploy, host change, or stack decision, confirm the LIVE state with your
own eyes -- a canonical/default/memory doc is a hint, never ground truth. The one rule: **the
deployed host is the source of truth, not a doc about it.** Run three checks cheapest-first --
live response headers (`curl -sI <domain>`), the real repo config (`wrangler.jsonc` vs
`vercel.json`/Next config), and DNS -- then apply precedence (a product's own deploy doc beats
the generic `project_canonical_stack` default) and gate the action (deploy is reversibility=N:
confirm target + blast radius with the user before executing). Output is a one-line verdict:
`TARGET CONFIRMED: <product> -> <host> (evidence) | go / hold`. The single most common way this
goes wrong: skipping the live check because the doc "looks authoritative" -- which is exactly the
stale-doc trap that this skill exists to break.

---

## Why this exists

An agent can burn a large token spend deploying a product to the wrong platform -- because a
generic stack default says "Vercel default" and that stale claim is trusted over the fact that
the product is actually live on another host (`Server: cloudflare`, confirmable by a one-line
`curl`). When no verify-against-reality step runs before an expensive, hard-to-walk-back action,
a five-second header check that would have caught it never happens.

The deeper failure is a class, not a one-off: canonical docs drift, products each carry their own
deploy reality, and "what's actually live" is the only authority that does not go stale. Any agent
about to deploy, repoint DNS, or pick a platform off a written claim is one stale line away from
the same waste. This skill makes the reality check a deliberate, invocable step with concrete
commands -- so the host is confirmed before tokens or production are spent, not after.

It pairs with an always-on line-wide deploy-verify rule (every agent inherits it; this skill is
the on-demand procedure with the actual commands) and duplicates neither.

---

## Step 1 -- Name the product and find its OWN deploy doc

State which product/site is being deployed, then read its product-specific deploy doc FIRST --
not the generic stack default. That is the per-product deploy note in your repo (or a per-product
deploy doc where one exists). The product doc is higher-precedence than a generic canonical-stack
default (which is a default for NEW greenfield builds, never a live-host claim about an existing
product). If the two disagree, the product doc plus live reality win -- continue to Step 2 to
confirm.

## Step 2 -- Verify against reality (three checks, cheapest first)

Run these against the actual deployed surface. Stop as soon as you have an unambiguous answer.

**(a) Live response headers -- the fastest ground truth (nearly free):**

```bash
curl -sI https://<domain> | grep -iE "server|cf-ray|cf-cache-status|x-vercel-id|x-vercel-cache|via"
```

Read the signal:

- `Server: cloudflare` + `CF-RAY:` + `CF-Cache-Status:` -> Cloudflare (Worker/Pages).
- `x-vercel-id:` / `x-vercel-cache:` / `Server: Vercel` -> Vercel.
- `Server: GitHub.com` -> GitHub Pages. `x-amz-*` / `Server: AmazonS3` -> S3/CloudFront. `Fly-Request-Id` -> Fly.io.

**(b) The real repo config -- what actually ships:**

- `wrangler.jsonc` / `wrangler.toml` present and real -> Cloudflare. Note the worker `name` and `main`/assets binding.
- `vercel.json` / a Next deploy config wired to Vercel -> Vercel.
- The config in the source tree is truth; a memory note describing it is not. If a build adapter is in play (e.g. `@opennextjs/cloudflare`), the adapter target is the host, not the framework.

**(c) DNS -- only when a cutover/repoint is the question:**

- Check apex/CNAME records and nameservers for the domain (`dig`/`nslookup`, or the registrar/CF dashboard). Confirm where the record points and which NS is authoritative before proposing any change.

## Step 3 -- Reconcile doc vs reality; surface any contradiction

Compare what the doc claimed to what reality shows.

- **Match** -> the doc is current; proceed.
- **Mismatch** -> reality wins. Say so plainly, and flag the stale doc for correction (fix the
  frontmatter/retrieval-hook, add a `last-verified` stamp) so it does not bite the next agent.
  A canonical-vs-canonical or canonical-vs-reality conflict is a standing contradiction worth
  tracking -- surface it, do not silently follow the doc.

## Step 4 -- Gate the action (deploy is reversibility=N)

No deploy / DNS change / "make X live" executes without an explicit user confirm of:

1. **Target** -- the platform/host (now reality-confirmed, not doc-assumed).
2. **Blast radius** -- does this touch a live production surface, existing routes (e.g. A2P/legal
   pages, payment webhooks), or DNS? What is the rollback?
3. **Cost shape** -- if it is a token-expensive multi-step deploy, the wrong target is the costliest
   miss; gate it hardest.

Confirm target + blast radius before spending tokens or touching prod. The old/current deployment
is the rollback -- do not destroy it as part of the cutover.

## Step 5 -- Emit the verdict

One line, evidence-bearing:

```
TARGET CONFIRMED: <product> -> <host>  | evidence: <Server header / config file / DNS> | <go | hold for user confirm>
```

Example: `TARGET CONFIRMED: example.com -> Cloudflare | evidence: Server: cloudflare + CF-RAY, wrangler.jsonc | hold for DNS-cutover confirm`.

---

## Anti-patterns (refuse list)

Inherits the house voice rules (forbidden vocab + forbidden patterns). Plus:

- **Preamble.** First line of output IS the verdict. Never "Let me check the deploy target".
- **Trusting the doc over the wire.** A canonical/default/memory claim about the host is a hint.
  If you have not run the live check, you do not know the target -- you are guessing.
- **Treating a generic canonical-stack default as a live-host claim.** It is a generic default
  for NEW builds. A product's own deploy doc plus reality override it, always.
- **Deploying without a confirmed target + blast radius.** Reversibility=N. No silent cutover.
- **Destroying the old deployment during cutover.** The current live surface is the rollback;
  keep it until the new target is verified live.
- **Leaving a stale doc unfixed after catching it.** If reality contradicted the doc, correct the
  doc's hook/frontmatter so the next agent does not repeat the miss.
- **Forbidden vocab** per the house voice rules: elegant, premium, delightful, magical, deep dive,
  as an AI, great question, happy to help, let's dive in.

---

## Definition of done (universal)

Done means: the deliverable exists at a named path (or the verdict is stated outright), every factual claim in it was checked against the live system rather than assumed, and the next action is named. Work you still have to verify is not done.

For Deploy Reality Check specifically: the host was confirmed against the live wire BEFORE any
token-expensive or irreversible action, the verdict names the evidence, and no deploy fired at a
doc-assumed target that reality would have contradicted. Zero wrong-platform deploys.
