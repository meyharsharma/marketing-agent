# Prompt Optimizer — Marketing Content Pipeline

## Required Skills

These skills MUST be used at the right time. Do not skip them.

| Skill | When to Use |
|-------|-------------|
| **`caption-writer`** | ALWAYS when writing the social media caption (the text that accompanies the post, NOT the text on the slide images). Also for hashtags and alt text. Contains voice rules, platform-specific lengths, and banned patterns. |
| **`skill-creator`** | When creating or iterating on a new skill. |
| **`notebooklm`** | When generating infographic content. Research via NotebookLM, generate image, download. |

## Generation Workflow

### 1. Parse the Request
- **Category**: `autopsy`, `did-you-know`, `prompt-drop`, `prompt-pattern`, `infographic`, `user-story`
- **Topic**: subject to build the post around
- **ICP**: audience profile (default: `solo-builder`)
- **Platform**: which platform (ask if not specified)

### 2. Load Context
Read these before generating anything:
1. `config/brand.yaml` — product info, voice, differentiators
2. `config/platforms/{platform}.yaml` — platform constraints, category rules
3. `config/icps/{icp}.yaml` — target audience profile
4. `prompts/{platform}/{category}.md` — exact output structure

### 3. Generate Content
Follow the prompt template structure exactly. For interactive categories (e.g. `autopsy`), generate initial content then pause and ask the user for the optimized prompt from Prompt Optimizer before completing. The text on slide images comes from the prompt template. The outer caption that accompanies the post uses the **caption-writer skill**.

### 4. Save Output
Save to `output/{platform}/{category}/{YYYY-MM-DD}_{slug}.md` using the standard frontmatter + sections format. If file exists, append a number (`-2`, `-3`).

### 5. Render Slides
```bash
python3 scripts/render_carousel.py templates/{category}.yaml content.yaml [slug]
```
Output: `generated_slides/{slug}/` with one PNG per slide.

For infographics: use `/notebooklm` skill (NotebookLM generation, not render_carousel.py).

### 6. Schedule (Optional)
```bash
python3 scripts/schedule_post.py <markdown_file> --schedule "YYYY-MM-DD HH:MM"
python3 scripts/schedule_post.py <file> --queue    # Add as draft
python3 scripts/schedule_post.py <file> --now       # Post immediately
```
Requires `BUFFER_ACCESS_TOKEN` and `IMGBB_API_KEY` in `.env`.

## Output Markdown Format

```markdown
---
platform: instagram
category: autopsy
topic: "fix my code"
icp: solo-builder
date: 2026-03-14
status: draft
---

# [Post Title]

## Slides
### Slide 1 — [Title]
[content]

## Caption
[caption text — use caption-writer skill]

## Hashtags
[hashtags — use caption-writer skill]

## Alt Text
[descriptions — use caption-writer skill]
```

## Rules

1. **Always read configs before generating.** Config files are source of truth.
2. **Follow prompt template structure exactly.**
3. **Use the caption-writer skill for ALL captions.** Never write captions without it.
4. **For autopsy posts:** the optimized prompt comes from the user. Always pause and ask.
5. **For user stories:** never fabricate testimonials. Real experiences only.
6. **For infographics:** use the notebooklm skill.

## Web UI

**Start:** `python3 web/app.py` (http://localhost:5000)

- `web/app.py` — Flask routes, config loading, generation logic
- `web/static/` — CSS + JS
- `web/templates/` — Jinja2 templates

Generation modes:
- **Instant** (did-you-know): Renders slide from content bank (~3s), caption via Claude in background
- **Full** (other categories): `claude -p --max-turns 1`, then renders slides

## Playwright Self-Check (MANDATORY)

**After ANY change to web UI files, run a Playwright check before telling the user it's done.**

1. Ensure server is running on port 5000
2. Navigate pages, take screenshots to `/tmp/web_check_*.png`
3. Read screenshots with the Read tool to visually verify
4. If broken: fix, restart server, re-check. Repeat until clean

## Key Paths

| What | Where |
|------|-------|
| Config | `config/brand.yaml`, `config/platforms/`, `config/icps/` |
| Prompt templates | `prompts/{platform}/{category}.md` |
| Output posts | `output/{platform}/{category}/` |
| Slide images | `generated_slides/{slug}/` |
| Carousel templates | `templates/{name}.yaml` + `templates/{name}/` |
| Content bank | `content-strategy.md` |
| Web UI | `web/` |
| Skills | `.claude/skills/` |
