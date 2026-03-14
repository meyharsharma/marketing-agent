# Prompt Architecture — Instagram Infographic Generation Instructions

## Before Generating

Read these config files and use their data throughout:
- `config/brand.yaml` — product info, voice, differentiators
- `config/platforms/instagram.yaml` — image constraints and visual style
- `config/icps/{icp}.yaml` — target audience profile

## What You're Creating

A single Instagram image post (1080x1080 or 1080x1350): **dark/black background with white text and accent colors**. The image breaks down the anatomy of a great prompt for a specific use case — as a diagram, checklist, comparison, or structured framework.

This is purely educational content. It positions Prompt Optimizer as an authority without selling.

## Output Structure

---

### Visual Description

Describe the image layout in precise detail so a designer (or image generation tool) can create it:

- **Layout type**: vertical stack, two-column comparison, checklist, flowchart, numbered list, or layered diagram
- **Section breakdown**: what goes where on the image, top to bottom
- **Visual hierarchy**: what's largest/boldest, what's secondary, what's fine print
- **Color usage**: dark/black background, white primary text, 1-2 accent colors for emphasis/sections
- **Icons or visual elements**: arrows, checkmarks, divider lines, section markers — describe what's needed
- **Typography notes**: headline size vs body vs labels

Be specific enough that someone could recreate this without asking questions.

---

### Text Content

All text that appears on the image, organized by position:

**Headline** (top of image):
- Under 10 words
- Bold, attention-grabbing
- States what this infographic teaches

**Sections/Elements** (the body):
- Each section with its label and content
- For checklists: each item on its own line
- For diagrams: each layer/node labeled with a brief description
- For comparisons: left column vs right column clearly separated
- Keep each element concise — this must be readable on a phone screen

**Closing Line** (bottom, before branding):
- A memorable, quotable insight that encapsulates the post's lesson
- Should feel like a takeaway someone would screenshot

**Branding** (bottom corner):
- Prompt Optimizer handle/logo only
- Small, subtle — not a CTA unless this is a product-mentioning post (rare)

---

### Caption

Write an Instagram caption (under 2200 characters) with this structure:

1. **Educational hook** (first sentence — shows in preview). Teach something immediately or pose a question that makes them want to read the image. Do NOT start with "We" or the product name.
2. **Context beyond the image** (2-4 sentences). Add depth that the image couldn't fit. A real-world example, a nuance, or a "why this matters" explanation.
3. **Engagement CTA** (final line). Drive saves and shares:
   - "Save this for your next [use case]."
   - "Which of these do you skip most often? Be honest."
   - "Share this with someone who still uses one-line prompts."

Voice: Match `config/brand.yaml` voice guidelines. Confident, not preachy. Technical but accessible.

---

### Hashtags

Generate 15 hashtags in three tiers:
- **5 high-volume** (500K+ posts): broad AI and tech terms
- **5 mid-volume** (50K-500K): developer tools, AI productivity
- **5 niche** (under 50K): prompt optimization specific

Format: space-separated, each starting with #

---

### Alt Text

Write thorough alt text describing:
- The overall layout of the infographic
- All text content on the image
- Visual elements (arrows, checkmarks, color coding)
- Enough detail for a screen reader user to get the full value of the post

---

## Post Type Variations

Use these as structural starting points depending on the topic:

**Layered Diagram** (e.g., "The 6 Layers of a Claude Prompt"):
- Vertical stack showing layers from top to bottom
- Each layer color-coded with a one-line description
- Shows the building blocks of a great prompt

**Side-by-Side Comparison** (e.g., "ChatGPT vs Claude: Prompt Structure"):
- Two columns, same task, different optimal structures
- Callout boxes highlighting key differences
- Educational AND differentiating — demonstrates model-aware thesis visually

**Decision Tree / Flowchart** (e.g., "Why 80% of AI Prompts Fail Before the First Word"):
- Visual flow showing decisions that happen before typing a prompt
- Highlights what most people skip
- Reveals the gap between what people do and what they should do

**Checklist** (e.g., "The One-Shot Prompt Checklist"):
- Clean checkbox format, 6-8 items
- Designed to look like something someone would screenshot and pin
- Each item specific and actionable (not vague like "be clear")
- This is the ONE post type that can include a subtle product CTA at the bottom

## Quality Rules

- This is EDUCATIONAL content. No selling except optional subtle branding.
- Content must be genuinely useful standalone — someone should want to save/screenshot this
- Every point must be specific and actionable — no generic advice like "provide context"
- If comparing models, be accurate about real differences in how they handle prompts
- Design descriptions must be specific enough to execute without interpretation
- All text must be readable at mobile size — if you're cramming too much, cut content
- Write for someone who is smart, busy, and will judge this in 2 seconds
