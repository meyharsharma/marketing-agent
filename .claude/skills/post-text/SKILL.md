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
| payoff | Takeaway | Hardcoded CTA (auto-filled) |

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

### Text limits
- **fact**: Max **150 characters**. The fact + detail combined
- Text is centered in a constrained area (480px wide for phone, similar for character)
- 1-2 sentences: the surprising fact + one line of why it matters

---

## Category: User Story

**Dimensions:** 1080x1350px (notebook on coral/cream/black backgrounds)
**Font:** PaytoneOne 118px for hook title / OpenSans 34px for body
**Slides:** hook + old_way + the_switch + result + payoff + cta (5-6 total)
**Template:** `templates/user-story/`

### Slide text limits
| Slide | Field | Max | Notes |
|-------|-------|-----|-------|
| hook | `hook_title` | 50 characters | Large text inside notebook. Short punchy problem statement |
| old_way | `body_text` | 150 characters | What they were doing before. Third person |
| the_switch | `body_text` | 150 characters | The moment they tried Prompt Optimizer |
| result | `body_text` | 120 characters | The outcome |
| result | `quote_text` | 80 characters | Optional direct quote |
| payoff | `body_text` | 120 characters | The lesson/takeaway |
| cta | `cta_headline` | 30 characters | CTA headline |

### User story voice
- Third person, proper narrative sentences
- Never fabricate testimonials
- Real experiences only

---

## Highlight Word Selection (prompt-pattern and prompt-drop only)

The `highlight` gets a red background. Choose words that:
- Are 1-2 words capturing the slide's core concept
- Are nouns or action verbs
- Never include: the, a, an, in, on, for, you, your, it, its, is, are

**Good:** `Scope Narrowing`, `Context`, `Format Lock`, `Role Frame`, `Every Model`
**Bad:** `The Problem`, `Your Prompt`, `Before:`, `In Practice`, `Heading:`
