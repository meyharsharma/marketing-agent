# Did You Know — Instagram Single Image Generation Instructions

## Before Generating

Read these config files and use their data throughout:
- `config/brand.yaml` — product info, voice, differentiators
- `config/platforms/instagram.yaml` — platform constraints and visual style
- `config/icps/{icp}.yaml` — target audience profile

## What You're Creating

A single Instagram image (1080x1080) that presents one surprising fact about how AI models process prompts. The goal: make someone stop scrolling and think "wait, really?"

## Content Rules

1. **One fact per post.** Never combine multiple facts.
2. **The fact must be genuinely surprising** — something most daily AI users don't know.
3. **Ground it in the Prompt Optimizer codebase.** These facts come from the model-specific guides in the product. They are real technical behaviors, not generic AI trivia.
4. **No hype language.** State the fact plainly. The surprise does the work.
5. **Keep it under 30 words on the image.** The caption expands on the fact.

## Output Structure

### Image Content

**Fact line** (large, coral text, uppercase):
The surprising fact in one punchy sentence. Under 15 words.

**Explanation** (smaller, white text):
One sentence explaining why this matters or what to do about it. Under 20 words.

### Caption

1. **Hook** (first line, shows in preview): Restate or tease the fact as a question or provocative statement.
2. **Expand** (2-3 sentences): Explain the technical "why" behind the fact. Reference the specific model behavior.
3. **Actionable takeaway** (1 sentence): What should the reader do differently?
4. **CTA** (final line): Drive saves or comments. "Save this for your next [model] session." or "Did you know this? Drop a comment."

### Hashtags

15 hashtags in three tiers:
- 5 high-volume (500K+): broad AI/tech
- 5 mid-volume (50K-500K): prompt engineering, AI productivity
- 5 niche (under 50K): model-specific, prompt optimization

### Alt Text

Describe the image: background color, text content, layout, and branding elements.

## Quality Rules

- The fact must be technically accurate — sourced from model documentation or the PO codebase
- No product pitching. The fact stands alone. Brand presence is the handle only.
- Write for someone who uses AI daily but hasn't studied prompt engineering
- The caption should make the reader feel smarter, not sold to
