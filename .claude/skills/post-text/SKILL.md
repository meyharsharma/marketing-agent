---
name: post-text
description: Generate the text content that goes ON the slide images for Prompt Optimizer marketing posts. Use this whenever generating slide content for any category (prompt-pattern, prompt-drop, autopsy, did-you-know, user-story). This is NOT for captions (use caption-writer for that). This controls the heading and body text rendered onto each slide image. Activates when generating post content, creating slides, or when the web UI renders carousel slides.
---

# Post Text Generator

Generate text that appears ON the slide images. This text gets rendered into PNG slides via HTML/CSS templates. It is NOT the caption (use caption-writer for that).

## Universal Rules (All Categories)

1. **Every sentence must be complete.** Never cut mid-word or mid-thought
2. **No markdown.** No `**bold**`, `` `backticks` ``, `# headers`, `- lists`. Plain text only
3. **No em dashes.** Use commas, periods, or semicolons
4. **No emojis** on slides

## Category: Prompt Pattern

**Dimensions:** 1080x1350px
**Font:** Poppins Bold, 90px heading / 34px body
**Slides:** hook + 3-4 technique steps + payoff (5-6 total)
**Template:** `templates/prompt-pattern/`

### Heading area
- Position: y=440px, 880px wide
- Max: **6 words** for the heading text
- Split into `before` (white) + `highlight` (red bg) + `after` (white)
- Highlight = 1-2 key nouns/verbs (not articles, prepositions, or pronouns)

### Body area
- Position: y=830px, 880px wide, 34px font
- Max: **200 characters** (~6-8 lines)
- 1-3 complete sentences, concrete and specific

### Per-slide guide
| Slide | Heading (4 words max) | Body (200 chars max) |
|-------|----------------------|---------------------|
| hook | Pattern name | One provocative line (~80 chars) |
| technique 01 | The problem | What goes wrong without this pattern |
| technique 02 | The fix | How the pattern works with example |
| technique 03 | Before/after or proof | Concrete demonstration |
| technique 04 | Why it works | Underlying model behavior |
| payoff | "Save this Post" (hardcoded) | CTA to Prompt Optimizer (hardcoded) |

---

## Category: Prompt Drop

**Dimensions:** 1080x1350px
**Font:** 
**Slides:** 
**Template:** `templates/prompt-drop/`

### Heading area


### Body area


### Per-slide guide


---

## Category: Autopsy

**Dimensions:** 1080x1080px
**Font:** OpenSans Condensed, 148px hook / 100px dissection heading / 40px body
**Slides:** hook + model_hears + 2-3 dissections + optimized + payoff (5-7 total)
**Template:** `templates/autopsy/`

### Slide text limits
| Slide | Field | Max |
|-------|-------|-----|
| hook | `prompt_text` | 40 characters (the bad prompt in quotes) |
| hook | `hook_line` | 60 characters (the curiosity line) |
| model_hears | `content` | 120 characters |
| dissection | `title` | 20 characters (failure name) |
| dissection | `body` | 100 characters (why this fails) |
| optimized | `prompt` | 200 characters (from user, used as-is) |
| payoff | `heading` | 20 characters |
| payoff | `body` | 80 characters |

---

## Category: Did You Know

**Dimensions:** 1080x1080px
**Font:** Montserrat, 34px fact text (centered in phone/character frame)
**Slides:** 1 (fact_a = phone mockup, fact_b = character illustration)
**Template:** `templates/did-you-know/`

### What to generate
Given a topic, write a fact that makes someone stop scrolling and think "wait, really?"

1. **Sentence 1**: The surprising fact. Bold, specific, concrete.
2. **Sentence 2**: Why it matters or what to do about it. This is the payoff.
3. Total: **80-140 characters**. Aim for ~100-120 chars. Too short feels thin, too long overflows.

### Text limits
- **fact**: **80-140 characters** target range. Hard max 150.
- Text is bold (MontserratEB 800) centered in a constrained area
- Auto-scales: short text grows bigger, long text shrinks. But 80-140 is the sweet spot for readability.
- MUST be exactly 2 sentences. Not 1 (too thin), not 3 (too long).
- No em dashes. No markdown formatting.

### Output format
Output as markdown with an ## Image Content section:
```
## Image Content

[The 2-sentence fact text, 80-140 characters, plain text, no labels]
```

### Examples (good — engaging, 2 sentences, right length)
- "Claude was trained to read XML tags as structure. Wrap your instructions in them and watch accuracy jump." (105 chars)
- "GPT-4o weights the last instruction 3x more than the first. Put your most critical constraint at the end." (106 chars)
- "Adding 4 words of role context saves 37% of tokens on average. The model stops hedging and commits." (99 chars)

### Examples (bad)
- "AI models weight the end of your prompt heaviest." (49 chars — too short, only 1 sentence, no payoff)
- "Negative instructions backfire. Saying 'don't be formal' makes models think about formality. Saying 'be conversational' works better because it gives a target, not an avoidance." (177 chars — 3 sentences, way over limit)

---

## Category: User Story

**Dimensions:** 1080x1350px (notebook on coral/cream/black backgrounds)
**Font:** PaytoneOne 118px for hook title / OpenSans 34px for body
**Slides:** hook + old_way + the_switch + result + payoff + cta (6 total)
**Template:** `templates/user-story/`

### Slide text limits
| Slide | Field | Max | Notes |
|-------|-------|-----|-------|
| hook | `problem` | **25 characters** | Large 118px font in notebook. 3-4 short words MAX. Must not break mid-word. Examples: "20 Minutes. Zero Output." or "I Almost Gave Up." |
| hook | `hook_line` | 60 characters | Not currently rendered but stored for caption context |
| old_way | `heading` | 25 characters | ALL CAPS heading above body text |
| old_way | `body` | 150 characters | What they were doing before. Third person narrative |
| the_switch | `heading` | 25 characters | ALL CAPS heading |
| the_switch | `body` | 150 characters | The moment they tried Prompt Optimizer |
| result | `heading` | 25 characters | ALL CAPS heading |
| result | `body` | 120 characters | The outcome, time saved, quality difference |
| result | `quote` | 80 characters | Optional direct quote from user |
| payoff | `heading` | 25 characters | ALL CAPS heading |
| payoff | `body` | 120 characters | The lesson or takeaway |
| cta | `cta_headline` | 30 characters | Hardcoded: "Try it for Free" |
| cta | `cta_url` | 30 characters | Hardcoded: "promptoptimizr.com" |
| cta | `cta_sub` | 20 characters | Hardcoded: "link in bio" |

### CRITICAL: Hook text sizing
The hook `problem` field renders at 118px PaytoneOne inside a ~600px wide notebook. At this size, each character is ~75px wide. **Max 25 characters.** If text is longer, words WILL break mid-word (e.g., "Paragrap hs."). Keep it to 3-4 punchy words.

### Output format
Claude must output slides with `**Heading:**` and `**Body:**` labels:
```
### Slide 1 , The Problem
**Heading:** 3 Hours. Zero Output.
**Body:** Priya needed Claude to help structure a research paper...
```

### User story voice
- Third person with a made-up person name (e.g. Priya, Marcus, Lena), never generic "she/he/they"
- Never fabricate testimonials
- Real experiences only
- No markdown in the actual text values (no bold, backticks, headers)

---

## Highlight Word Selection (prompt-pattern and prompt-drop only)

The `highlight` gets a red background. Choose words that:
- Are 1-2 words capturing the slide's core concept
- Are nouns or action verbs
- Never include: the, a, an, in, on, for, you, your, it, its, is, are

**Good:** `Scope Narrowing`, `Context`, `Format Lock`, `Role Frame`, `Every Model`
**Bad:** `The Problem`, `Your Prompt`, `Before:`, `In Practice`, `Heading:`
