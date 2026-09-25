---
name: prompt-builder
description: >
  Structured XML prompt builder for Claude. Use this skill ANY time the user wants to write, structure, or improve a prompt -- whether they say "help me write a prompt," "draft me a prompt," "structure this prompt," "use XML tags," "build a prompt for X," "how should I prompt Claude to do Y," or asks about using role/task/context/examples/thinking/constraints/output tags. Also trigger when the user pastes a messy or vague prompt and asks Claude to "clean it up," "make it better," or "turn this into a proper prompt." The goal is to assemble a high-quality, structured prompt using Anthropic's recommended XML tagging pattern so Claude parses intent cleanly and produces better output every time.
---

# Prompt Builder

> ## Scope note
>
> **This skill is UNIVERSAL.** Any agent may invoke it.
>
> Auto-invoke heuristic (silent subagent — no confirmation question, no preamble) when ANY of:
>
> 1. The user says "draft me a prompt", "write a prompt", "give me a prompt", "I need a prompt", "build me a prompt", "structure this prompt", or pastes an unstructured prompt asking it be cleaned up.
> 2. The deliverable is a **shippable / external prompt** — system prompt for a product, Anthropic API call to deploy, agent brief to share, courseware, one-shot to resell, prompt to paste into another tool or session.
> 3. The user's first message is **>200 words AND not already structured** (no headers, XML tags, or labeled sections).
> 4. The receiving agent catches itself asking **2+ clarifying questions back-to-back** — the request was underspecified; structure it retroactively.
>
> **Skip when:** prompt is already structured (XML, headers, labeled sections), the ask is a short inline rewrite of an existing prompt fragment, it's a continuation of a known recurring workflow, or the user explicitly says "don't run it through prompt-builder."

Your job is to help the user construct a well-structured Claude prompt using XML tags. Each tag removes ambiguity and gives Claude a specific lens to work from. Use as many or as few tags as the task warrants — not every prompt needs all seven. Start with what's essential and add layers only when they add signal.

---

## The Seven Tags

### 1. `<role>`

Who Claude should be for this task — persona, expertise domain, tone, and audience.

```
<role>
You are a [ROLE/PERSONA] with expertise in [DOMAIN].
Your tone should be [TONE].
Your audience is [AUDIENCE].
</role>
```

**Why it matters:** Sets vocabulary, confidence level, and perspective. "Senior AV sales engineer" and "technical writer" will produce structurally different outputs for the same task.

---

### 2. `<task>`

What needs to be done — one specific objective with a success criterion.

```
<task>
I need you to [SPECIFIC TASK] so that [SUCCESS CRITERIA].
Be direct. No preamble. No fluff.
</task>
```

**Why it matters:** One task, one output. If you have multiple tasks, either sequence them in `<steps>` or break them into separate prompts.

---

### 3. `<context>`

Background information, documents, data, or situational detail Claude needs to do the task well.

```
<context>
[Paste documents, data, or background here]
</context>
```

**Tips:** Put long documents at the top of the prompt, your query at the end. Context is for information Claude can't infer — don't pad it with things Claude already knows.

---

### 4. `<examples>`

3–5 input/output pairs showing exactly what good looks like.

```
<examples>
Input: [example input]
Output: [ideal output]

Input: [example input]
Output: [ideal output]
</examples>
```

**Why it matters:** Examples are the highest-leverage element in any prompt. Claude will match your format, tone, and structure exactly. Cover both normal cases and edge cases.

---

### 5. `<thinking>`

Instruction for Claude to reason before answering — use when accuracy or multi-step logic matters.

```
<thinking>
Before answering, think through this step by step.
Use <thinking> tags for your reasoning.
Put only your final answer in <answer> tags.
</thinking>
```

**When to use:** Complex reasoning tasks, math, multi-step analysis, choices with trade-offs. Skip it for simple generation tasks — it adds tokens without benefit.

---

### 6. `<constraints>`

Hard rules Claude must follow — things to always do, never do, and what to do if it's about to break a rule.

```
<constraints>
Never [thing to avoid].
Always [thing to ensure].
If you are about to break a rule, stop and tell me.
</constraints>
```

**Tips:** Negative constraints ("never use bullet points") are as important as positive ones. Be specific — "be concise" is weak; "maximum 3 paragraphs" is strong.

---

### 7. `<output>`

The exact format, structure, and wrapper for the response.

```
<output>
Return your response as [JSON / markdown / table / prose].
Use this exact structure: [structure template].
Wrap your output in <result> tags.
</output>
```

**Prefill trick:** You can also add a prefill line after the prompt to skip Claude's preamble:

```
Start your response with exactly this: {"analysis":
```

Claude will continue from there, skipping any setup language.

---

## How to Build a Prompt

1. **Understand the task** in one sentence. What is Claude producing and for whom?
2. **Fill the required tags first** — `<role>` and `<task>` are almost always needed. `<output>` is needed whenever format matters.
3. **Add supporting tags** — `<context>` if there's background Claude needs, `<examples>` if format precision matters, `<constraints>` if there are hard rules, `<thinking>` if it's a reasoning-heavy task.
4. **Skip what doesn't add signal.** A 3-tag prompt that's tight beats a 7-tag prompt with filler.
5. **Show the assembled prompt** in a clean code block, ready to copy-paste.
6. **Offer one refinement pass** — ask if the role, constraints, or output format need adjusting.

---

## Token Efficiency Note

Long prompts cost more tokens — and in long conversations, the entire history replays with every message (the "token snowball effect"). Keep prompts lean. For complex workflows, break them into separate focused sessions rather than one sprawling conversation. One task per session = faster, cheaper, better output.

---

## Example User Context (Customize Per Install)

When building prompts, apply these defaults unless the user says otherwise:

- **Role default:** Senior Sales Director at [Your Company], [your industry, your customer segment]
- **Tone:** Professional, direct, no buzzwords, no bullet-pointed emails
- **Output default:** Clean prose, sign off in your preferred style
- **Common tasks:** Cold outreach emails, SOW/scope documents, prospect research, deal evaluations, CRM import prep, prospecting pipeline runs

---

## Full Example

**Prompt for:** VP-level cold outreach email to a target account

```
<role>
You are a senior Sales Director at [Your Company] specializing in [your service offering for your customer type]. You write direct, executive-level cold outreach — no buzzwords, no fluff.
Your audience is VP and C-Suite decision-makers at target accounts.
</role>

<task>
Write a cold outreach email to a [Decision-Maker Role] at a mid-size target company who has never heard of [your employer].
Success: They open it, read it in under 30 seconds, and respond or forward it internally.
</task>

<context>
[your employer] recently completed an $8M broadcast-grade event space for a major tech campus.
We specialize in conference rooms, boardrooms, digital signage, and managed AV services.
Key differentiator: managed services built in from day one — no orphaned systems.
</context>

<examples>
Bad opener: "I hope this finds you well. My name is [Product Owner] and I wanted to reach out..."
Good opener: "Most enterprise AV programs share the same problem: the systems look great on paper, get installed, and then quietly become IT's least favorite responsibility."
</examples>

<constraints>
Never use: "I hope this finds you well," "synergy," "leverage," "experiential," bullet points.
Never open with your name or company name.
Maximum 3 short paragraphs.
</constraints>

<output>
Plain text, Outlook-ready.
Subject line format: [Topic] | [Company]
End with: Cheers,
No name or signature after it.
</output>
```
