# Prompt Autopsy — Instagram Carousel Generation Instructions

## Before Generating

Read these config files and use their data throughout:
- `config/brand.yaml` — product info, voice, differentiators
- `config/platforms/instagram.yaml` — carousel constraints and visual style
- `config/icps/{icp}.yaml` — target audience profile

## What You're Creating

An Instagram carousel where each slide is a separate image: **dark/black background with white text overlaid**. The carousel dissects a bad prompt, shows why it fails, and reveals the optimized version.

Core narrative: **The failure isn't the model — it's the language mismatch.**

## IMPORTANT: Two-Step Interactive Workflow

This post type requires **two steps** because the optimized prompt comes from the user (via Prompt Optimizer), not from Claude Code.

### Step 1 — Generate & Pause
Generate the bad prompt, the "what the model hears" analysis, and the dissection slides. Then **STOP and present the bad prompt to the user**. Ask them to run it through Prompt Optimizer and provide the optimized version.

Output for Step 1:
```
Here's the bad prompt for this autopsy:

"[the bad prompt]"

Please run this through Prompt Optimizer and paste back the optimized version.
I'll use it for the "Optimized Version" slide and complete the post.
```

### Step 2 — Complete the Post
Once the user provides the optimized prompt, use it as-is for the Optimized Version slide. Then generate the payoff slide, caption, hashtags, and alt text to complete the post.

---

## Slide-by-Slide Structure

Each slide below becomes one image in the carousel. Keep text per slide to ~40-60 words max — it must be readable on a phone screen.

---

### Slide 1 — The Hook

**Purpose**: Stop the scroll. Create enough curiosity to swipe.

Content:
- The bad prompt in large, quoted text (exactly as someone would type it)
- A hook line underneath that creates tension or curiosity
- Example hook patterns:
  - "This prompt wastes 90% of the model's capability."
  - "You've typed this. The output was garbage. Here's why."
  - "This looks fine. It's actually broken in 5 ways."

Design notes: The bad prompt should be the visual centerpiece. Hook line smaller below it.

---

### Slide 2 — What the Model "Hears"

**Purpose**: Reveal the gap between intent and interpretation.

Content:
- Split into two sections: "What you said" vs. "What the model heard"
- Show how the model interprets each vague part of the prompt
- Highlight ambiguities the model must guess about
- Keep it concrete — specific misinterpretations, not abstract complaints

Design notes: Two-column or top/bottom split. Use a contrasting accent color for the "model heard" section.

---

### Slides 3 through N-2 — The Dissection (one failure per slide)

**Purpose**: Educate. Each slide isolates ONE specific failure pattern.

Content per slide:
- **Failure name** as a bold header (e.g., "Missing Role Frame", "No Output Format", "Zero Context", "No Constraints", "Ambiguous Task Scope")
- 1-2 sentences explaining why this specific gap degrades the output
- Optionally: a one-line "what to do instead" hint

Rules:
- One concept per slide. Never combine failures.
- Name the pattern — it should feel like a diagnostic label
- The explanation should make the reader think "oh, I do that"
- Use 2-4 dissection slides depending on the prompt (more failures = more slides, up to the max)

Design notes: Failure name large at top. Explanation text below. Clean, minimal layout.

---

### Slide N-1 — The Optimized Version (uses user-provided prompt)

**Purpose**: Show the proof. This is the payoff.

Content:
- The optimized prompt **provided by the user** (from Prompt Optimizer) — use it exactly as given
- A small label indicating which model it was optimized for
- Do NOT modify the user's optimized prompt — it is the real product output

Rules:
- Display the optimized prompt as-is from the user
- If the prompt is long, it's okay to use slightly smaller text — but it must still be readable
- Do NOT explain the prompt on this slide — just show it. The dissection slides already did the explaining.

Design notes: The optimized prompt as a clean text block. Model label in top corner or as a small tag.

---

### Slide N (Final) — The Payoff Line

**Purpose**: A memorable closing insight + subtle branding.

Content:
- One punchy line that reframes the lesson from this autopsy
- Pattern: shift blame from the model to the prompt
  - "The model isn't bad at debugging. It just didn't know what broke."
  - "AI isn't generic. Your prompt was."
  - "The model gave you exactly what you asked for. That's the problem."
- Subtle Prompt Optimizer branding: just the logo/handle, no hard sell

Design notes: The payoff line centered and large. Branding small in the corner.

---

## Caption

Write an Instagram caption (under 2200 characters) with this structure:

1. **Hook line** (first sentence — this shows in the preview before "...more"). Must stop the scroll. Can be provocative, relatable, or surprising. Do NOT start with "We" or the product name.
2. **Expand on the lesson** (2-4 sentences). What's the deeper insight from this autopsy? Speak directly to the Solo Builder's experience.
3. **Engagement CTA** (final line). Drive comments, saves, or shares. Examples:
   - "What prompt do you want us to autopsy next? Drop it below."
   - "Save this for the next time you're about to type [bad prompt]."
   - "Tag someone who needs to see this before their next ChatGPT session."

Voice: Match `config/brand.yaml` voice guidelines. Confident, not preachy. Technical but accessible.

## Hashtags

Generate 15 hashtags in three tiers:
- **5 high-volume** (500K+ posts): broad AI and tech terms
- **5 mid-volume** (50K-500K): developer tools, AI productivity, prompt-related
- **5 niche** (under 50K): specific to prompt optimization, model-specific terms

Format: space-separated, each starting with #

## Alt Text

Write descriptive alt text for each slide image. Include:
- What text appears on the slide
- The visual layout and color scheme
- Enough detail for someone using a screen reader to understand the content

---

## Quality Rules

- The optimized prompt comes from the user — never generate it yourself
- No hype language (revolutionary, game-changing, unleash, supercharge)
- Educational tone — this should feel like learning something, not being sold to
- Product mentions: ONLY subtle branding on the final slide. No product pitching in the content slides.
- Every dissection point must be specific and actionable, not generic advice
- The hook must be visceral enough that someone who's felt this pain stops scrolling
- Write for someone who is smart, busy, and skeptical of marketing
