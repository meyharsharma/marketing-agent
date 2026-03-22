"""
Flask web UI for the marketing content pipeline.

Walks the user through: platform -> category -> topic -> generate -> preview -> schedule.
Single user, localhost only.

Usage:
    cd web && python3 app.py
    # or from project root:
    python3 web/app.py
"""

import os
import re
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

# ── Project paths ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Load .env into os.environ so subprocesses inherit the vars ───────
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"
SLIDES_DIR = PROJECT_ROOT / "generated_slides"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CONTENT_STRATEGY = PROJECT_ROOT / "content-strategy.md"

# ── Flask app ────────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=str(Path(__file__).parent / "static"),
    template_folder=str(Path(__file__).parent / "templates"),
)
app.secret_key = os.urandom(24)

# ── In-memory job store ──────────────────────────────────────────────
jobs = {}  # job_id -> {status, progress, output_path, slides_dir, error, params, ...}
job_lock = threading.Lock()

# ── Config loading ───────────────────────────────────────────────────

def load_brand():
    with open(CONFIG_DIR / "brand.yaml") as f:
        return yaml.safe_load(f)


def scan_platforms():
    """Return {platform_id: platform_config} from config/platforms/."""
    platforms = {}
    platforms_dir = CONFIG_DIR / "platforms"
    if platforms_dir.is_dir():
        for p in sorted(platforms_dir.glob("*.yaml")):
            with open(p) as f:
                data = yaml.safe_load(f)
            platforms[data.get("id", p.stem)] = data
    return platforms


def scan_icps():
    """Return {icp_id: icp_config} from config/icps/."""
    icps = {}
    icps_dir = CONFIG_DIR / "icps"
    if icps_dir.is_dir():
        for p in sorted(icps_dir.glob("*.yaml")):
            with open(p) as f:
                data = yaml.safe_load(f)
            icps[data.get("id", p.stem)] = data
    return icps


# ── Content bank parser ──────────────────────────────────────────────

def parse_content_bank():
    """
    Parse content-strategy.md to extract content bank tables per category.
    Returns {category_slug: [list of topic dicts]}.
    """
    if not CONTENT_STRATEGY.exists():
        return {}

    text = CONTENT_STRATEGY.read_text()
    banks = {}

    # Category mapping: section header number -> slug
    category_map = {
        "1": ("autopsy", ["bad_prompt", "hook"]),
        "2": ("did-you-know", ["fact", "detail"]),
        "3": ("prompt-drop", ["task", "target_model", "prompt_preview"]),
        "4": ("prompt-pattern", ["pattern_name", "core_insight"]),
        "5": ("infographic", ["title", "type", "notebooklm_source"]),
        "6": ("user-story", ["persona", "problem", "before_after"]),
    }

    # Split into sections by ### headers so each section is isolated
    sections = re.split(r'(?=^### \d+\.)', text, flags=re.MULTILINE)

    for num, (slug, columns) in category_map.items():
        # Find the section for this category number
        section = None
        for s in sections:
            if re.match(rf'### {num}\.', s.strip()):
                section = s
                break

        if not section:
            banks[slug] = []
            continue

        # Find the content bank table within this section
        table_match = re.search(
            r'\*\*Content bank.*?\n\|[^\n]+\n\|[-\s|]+\n((?:\|[^\n]*\n)*)',
            section, re.DOTALL,
        )
        if not table_match:
            banks[slug] = []
            continue

        rows_text = table_match.group(1).strip()
        entries = []
        for row in rows_text.split("\n"):
            row = row.strip()
            if not row or not row.startswith("|"):
                continue
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) < 2:
                continue
            # Skip rows that look like separators
            if all(re.match(r'^[-\s]*$', c) for c in cells):
                continue
            # Skip the # column
            cells = cells[1:]
            entry = {"id": len(entries) + 1}
            for i, col_name in enumerate(columns):
                entry[col_name] = cells[i].strip('"').strip() if i < len(cells) else ""
            entries.append(entry)
        banks[slug] = entries

    return banks


def _find_slides_dir(slug):
    """Find the slides directory for a slug, trying base slug without number suffix as fallback."""
    slides_path = SLIDES_DIR / slug
    if slides_path.exists():
        return slides_path
    # Try without trailing -N suffix (e.g. "context-injection-2" -> "context-injection")
    base_slug = re.sub(r'-\d+$', '', slug)
    if base_slug != slug:
        fallback = SLIDES_DIR / base_slug
        if fallback.exists():
            return fallback
    return slides_path  # Return original (non-existent) path


# ── Post scanning ────────────────────────────────────────────────────

def scan_posts():
    """Scan output/ for all generated post markdown files."""
    posts = []
    if not OUTPUT_DIR.exists():
        return posts

    for md_file in sorted(OUTPUT_DIR.rglob("*.md"), reverse=True):
        rel = md_file.relative_to(OUTPUT_DIR)
        text = md_file.read_text()

        # Parse frontmatter (gracefully handle malformed YAML)
        fm = {}
        fm_match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                fm = {}

        # Extract title
        title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
        title = title_match.group(1) if title_match else md_file.stem

        # Find slides
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", md_file.stem)
        slides_path = _find_slides_dir(slug)
        slide_images = sorted(slides_path.glob("*.png")) if slides_path.exists() else []
        thumbnail = str(slide_images[0].relative_to(SLIDES_DIR)) if slide_images else None

        posts.append({
            "path": str(rel),
            "filename": md_file.name,
            "title": title,
            "slug": slug,
            "category": fm.get("category", "unknown"),
            "platform": fm.get("platform", "instagram"),
            "status": fm.get("status", "draft"),
            "date": fm.get("date", ""),
            "topic": fm.get("topic", ""),
            "thumbnail": thumbnail,
            "slide_count": len(slide_images),
        })

    return posts


def parse_post(rel_path):
    """Parse a post markdown file into structured data."""
    full_path = OUTPUT_DIR / rel_path
    if not full_path.exists():
        return None

    text = full_path.read_text()

    # Frontmatter (gracefully handle malformed YAML)
    fm = {}
    fm_match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            fm = {}

    # Title
    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    title = title_match.group(1) if title_match else ""

    # Sections
    caption_match = re.search(r"## Caption\n\n?(.+?)(?=\n## |\Z)", text, re.DOTALL)
    caption = caption_match.group(1).strip() if caption_match else ""

    hashtags_match = re.search(r"## Hashtags\n\n?(.+?)(?=\n## |\Z)", text, re.DOTALL)
    hashtags = hashtags_match.group(1).strip() if hashtags_match else ""

    alt_match = re.search(r"## Alt Text\n\n?(.+?)(?=\n## |\Z)", text, re.DOTALL)
    alt_text = alt_match.group(1).strip() if alt_match else ""

    image_match = re.search(r"## Image Content\n\n?(.+?)(?=\n## |\Z)", text, re.DOTALL)
    image_content = image_match.group(1).strip() if image_match else ""

    # Slides
    slides = []
    slides_match = re.search(r"## Slides\s*\n(.*?)(?=\n## [^#]|\Z)", text, re.DOTALL)
    if slides_match:
        slide_pattern = r"### Slide \d+\s*[-\u2013\u2014,:]\s*(.+?)\n(.*?)(?=### Slide|\Z)"
        for m in re.finditer(slide_pattern, slides_match.group(1), re.DOTALL):
            slides.append({"title": m.group(1).strip(), "content": m.group(2).strip()})

    # Slide images
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", Path(rel_path).stem)
    slides_path = _find_slides_dir(slug)
    slide_images = []
    if slides_path.exists():
        slide_images = [str(p.relative_to(SLIDES_DIR)) for p in sorted(slides_path.glob("*.png"))]

    return {
        "path": rel_path,
        "frontmatter": fm,
        "title": title,
        "slug": slug,
        "caption": caption,
        "hashtags": hashtags,
        "alt_text": alt_text,
        "image_content": image_content,
        "slides": slides,
        "slide_images": slide_images,
    }


# ── Generation logic ────────────────────────────────────────────────

def _slugify(text):
    """Convert text to lowercase kebab-case slug."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[\s_]+', '-', text).strip('-')


def _extract_dyk_fact(md_text):
    """Extract the fact text from a did-you-know post markdown."""
    match = re.search(r'\*\*Fact:\*\*\s*(.+?)(?=\n\n|\Z)', md_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'## Image Content\n\n?(.+?)(?=\n## |\Z)', md_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


# Categories where the content bank provides enough data to render
# slides instantly, without waiting for Claude.
INSTANT_RENDER_CATEGORIES = {"did-you-know"}


def _make_output_file(platform, category, slug):
    """Create a unique output file path, avoiding overwrites."""
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_DIR / platform / category
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{today}_{slug}.md"
    counter = 2
    while output_file.exists():
        output_file = output_dir / f"{today}_{slug}-{counter}.md"
        counter += 1
    return output_file


def _render_slides(category, template_yaml, content_source, slug):
    """Run render_carousel.py and return (success, warning)."""
    if not template_yaml.exists():
        return True, None
    render_result = subprocess.run(
        ["python3", str(PROJECT_ROOT / "scripts" / "render_carousel.py"),
         str(template_yaml), str(content_source), slug],
        capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT),
    )
    if render_result.returncode != 0:
        return False, render_result.stderr or "Render had issues"
    return True, None


def _build_claude_prompt(platform, category, topic, icp, today):
    """Build the full prompt string for Claude CLI."""
    brand_text = (CONFIG_DIR / "brand.yaml").read_text() if (CONFIG_DIR / "brand.yaml").exists() else ""
    platform_text = (CONFIG_DIR / "platforms" / f"{platform}.yaml").read_text() if (CONFIG_DIR / "platforms" / f"{platform}.yaml").exists() else ""
    icp_text = (CONFIG_DIR / "icps" / f"{icp}.yaml").read_text() if (CONFIG_DIR / "icps" / f"{icp}.yaml").exists() else ""
    prompt_text = (PROMPTS_DIR / platform / f"{category}.md").read_text() if (PROMPTS_DIR / platform / f"{category}.md").exists() else ""

    # Load caption-writer skill rules
    caption_skill_path = PROJECT_ROOT / ".claude" / "skills" / "caption-writer" / "SKILL.md"
    caption_rules = ""
    if caption_skill_path.exists():
        caption_rules = caption_skill_path.read_text()
        caption_rules = re.sub(r'^---\n.*?\n---\n*', '', caption_rules, flags=re.DOTALL)
        caption_rules = f"CAPTION WRITING RULES (follow these exactly for the caption, hashtags, and alt text):\n\n{caption_rules}"

    # Inline slide text rules (extracted from post-text skill, kept short to avoid prompt bloat)
    post_text_rules = """SLIDE TEXT RULES (for the text ON each slide image, NOT the caption):
- Each slide has a heading (max 30-48 chars) and a body (max 200 chars for technique slides, max 80 chars for hook slides)
- Every sentence must be COMPLETE. Never cut mid-word or mid-thought. If too long, rewrite shorter
- No markdown formatting in slide text. No **bold**, no `backticks`, no # headers, no - list markers. Plain text only
- No em dashes
- Body text should be 1-3 complete sentences. Concrete and specific
- Keep heading to 3-5 words. The heading gets split into before/highlight/after for the red highlight effect"""

    autopsy_note = ""
    if category == "autopsy":
        autopsy_note = "\n\nIMPORTANT: For this autopsy post, generate everything EXCEPT the optimized prompt slide. Write [AWAITING_OPTIMIZED_PROMPT] as a placeholder for the optimized prompt. Generate all other slides, caption, hashtags, and alt text."

    return f"""Generate a {category} post for {platform} about: {topic}

Target ICP: {icp}

Here is the brand config:
---
{brand_text}
---

Here is the platform config:
---
{platform_text}
---

Here is the ICP profile:
---
{icp_text}
---

Here is the prompt template with exact instructions:
---
{prompt_text}
---

CRITICAL: Output ONLY the raw markdown content. Do NOT use any tools, do NOT write files, do NOT ask questions. Just output the complete post as plain text starting with the YAML frontmatter block.

{caption_rules}

{post_text_rules}

The output must start with --- and end with the last section. Use this frontmatter:
---
platform: {platform}
category: {category}
topic: "{topic}"
icp: {icp}
date: {today}
status: draft
---

Follow the prompt template structure exactly. Include all sections: Slides (for carousels) or Image Content (for single images), Caption, Hashtags, and Alt Text.{autopsy_note}
"""


def _run_claude_caption(job_id, platform, category, topic, icp, output_file):
    """Background: generate caption/hashtags/alt text via Claude, then update the markdown."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        claude_prompt = _build_claude_prompt(platform, category, topic, icp, today)

        result = subprocess.run(
            ["claude", "-p", claude_prompt, "--output-format", "text", "--max-turns", "1"],
            capture_output=True, text=True, timeout=180, cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            with job_lock:
                jobs[job_id]["caption_status"] = "error"
                jobs[job_id]["caption_error"] = result.stderr or "Claude CLI failed"
            return

        claude_output = result.stdout.strip()
        # Strip em dashes
        claude_output = claude_output.replace('\u2014', ',').replace('\u2013', ',')

        # Extract caption, hashtags, alt text from Claude's output
        caption_match = re.search(r'## Caption\n\n(.+?)(?=\n## |\Z)', claude_output, re.DOTALL)
        hashtags_match = re.search(r'## Hashtags\n\n?(.+?)(?=\n## |\Z)', claude_output, re.DOTALL)
        alt_match = re.search(r'## Alt Text\n\n?(.+?)(?=\n## |\Z)', claude_output, re.DOTALL)

        caption = caption_match.group(1).strip() if caption_match else ""
        hashtags = hashtags_match.group(1).strip() if hashtags_match else ""
        alt_text = alt_match.group(1).strip() if alt_match else ""

        # Update the existing markdown with generated caption sections
        existing = output_file.read_text()
        if "## Caption" not in existing and caption:
            existing += f"\n\n## Caption\n\n{caption}"
        if "## Hashtags" not in existing and hashtags:
            existing += f"\n\n## Hashtags\n\n{hashtags}"
        if "## Alt Text" not in existing and alt_text:
            existing += f"\n\n## Alt Text\n\n{alt_text}"
        output_file.write_text(existing)

        with job_lock:
            jobs[job_id]["caption_status"] = "complete"

    except Exception as e:
        with job_lock:
            jobs[job_id]["caption_status"] = "error"
            jobs[job_id]["caption_error"] = str(e)


def _run_generation_instant(job_id, params):
    """
    Instant generation for content-bank categories (did-you-know).
    Phase 1: Render slide from content bank data immediately (~3s).
    Phase 2: Generate caption via Claude in the background.
    """
    try:
        platform = params["platform"]
        category = params["category"]
        topic = params["topic"]
        topic_data = params.get("topic_data", {})
        variant = params.get("variant")
        icp = params.get("icp", "solo-builder")
        slug = _slugify(topic)
        today = datetime.now().strftime("%Y-%m-%d")

        with job_lock:
            jobs[job_id]["progress"] = "Rendering slide..."

        # Build content YAML from content bank data
        if category == "did-you-know":
            fact_text = topic_data.get("fact", topic)
            detail_text = topic_data.get("detail", "")
            # Combine fact + detail for the slide text
            slide_fact = f"{fact_text}. {detail_text}" if detail_text else fact_text
            variant_key = variant or "fact_a"
            content_data = {variant_key: {"fact": slide_fact}}
        else:
            content_data = {}

        # Write content YAML
        output_file = _make_output_file(platform, category, slug)
        content_yaml_path = output_file.with_suffix(".content.yaml")
        content_yaml_path.write_text(yaml.dump(content_data, default_flow_style=False))

        # Write initial markdown (slide content, no caption yet)
        md_text = f"""---
platform: {platform}
category: {category}
topic: "{topic}"
icp: {icp}
date: {today}
status: draft
---

# Did You Know: {topic_data.get('fact', topic)}

## Image Content

**Fact:** {topic_data.get('fact', topic)}. {topic_data.get('detail', '')}
"""
        output_file.write_text(md_text)
        rel_path = str(output_file.relative_to(OUTPUT_DIR))

        # Render slides (fast, ~2-3s)
        template_yaml = PROJECT_ROOT / "templates" / f"{category}.yaml"
        success, warning = _render_slides(category, template_yaml, content_yaml_path, slug)
        if warning:
            with job_lock:
                jobs[job_id]["render_warning"] = warning

        # Mark as complete immediately (slides are done)
        with job_lock:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = "Done! Generating caption in background..."
            jobs[job_id]["output_path"] = rel_path
            jobs[job_id]["slug"] = slug
            jobs[job_id]["caption_status"] = "generating"
            slides_path = SLIDES_DIR / slug
            if slides_path.exists():
                jobs[job_id]["slides_dir"] = str(slides_path.relative_to(PROJECT_ROOT))

        # Phase 2: Generate caption in background
        caption_thread = threading.Thread(
            target=_run_claude_caption,
            args=(job_id, platform, category, topic, icp, output_file),
            daemon=True,
        )
        caption_thread.start()

    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)


def _md_to_content_yaml(md_text, category):
    """
    Convert generated markdown slides to a content YAML matching the template's
    placeholder structure. Returns (content_dict, needs_yaml_file) or (None, False)
    if the category uses markdown-based rendering.
    """
    if category == "prompt-pattern":
        return _md_to_prompt_pattern_yaml(md_text), True
    if category == "prompt-drop":
        return _md_to_prompt_drop_yaml(md_text), True
    # autopsy, user-story: use markdown-based rendering in render_carousel.py
    return None, False


def _md_to_prompt_pattern_yaml(md_text):
    """Parse prompt-pattern markdown into hook/technique_N/payoff content YAML."""
    slides_match = re.search(r'## Slides\s*\n(.*?)(?=\n## [^#]|\Z)', md_text, re.DOTALL)
    if not slides_match:
        return {}

    slide_pattern = r'### Slide \d+\s*[-\u2013\u2014,:]\s*(.+?)\n(.*?)(?=### Slide|\Z)'
    slides = list(re.finditer(slide_pattern, slides_match.group(1), re.DOTALL))
    if not slides:
        return {}

    content = {}
    technique_idx = 1

    for i, m in enumerate(slides):
        title = m.group(1).strip().lower()
        body_text = m.group(2).strip()

        # Parse **Label:** Value format (Claude often uses this)
        heading_match = re.search(r'\*\*(?:Heading|Title|Hook|Pattern)\s*:\*\*\s*(.+?)(?=\n|$)', body_text)
        body_match = re.search(r'\*\*(?:Body|Text)\s*:\*\*\s*(.+?)(?=\n\*\*|\n\n|$)', body_text, re.DOTALL)

        if heading_match:
            # Labeled format: **Heading:** Value
            bold_lines = [heading_match.group(1).strip()]
            body_only = body_match.group(1).strip() if body_match else ''
        else:
            # Unlabeled format: **Bold heading**\nBody text
            all_bold = re.findall(r'\*\*(.+?)\*\*', body_text)
            bold_lines = [b for b in all_bold if not re.match(r'^(?:Body|Text|Heading)\s*:', b)]
            body_only = re.sub(r'\*\*[^*]+\*\*\s*', '', body_text).strip()
        body_lines = []
        for l in body_only.split('\n'):
            l = l.strip()
            if not l or l == '-':
                continue
            # Strip markdown list markers
            l = re.sub(r'^[-*]\s+', '', l)
            # Strip markdown inline formatting remnants
            l = l.replace('`', '').replace('*', '')
            # Strip markdown headers
            l = re.sub(r'^#+\s*', '', l)
            if l:
                body_lines.append(l)

        heading = bold_lines[0] if bold_lines else m.group(1).strip()
        # Strip label prefixes like "Heading:", "Title:", "Body:"
        heading = re.sub(r'^(?:Heading|Title|Hook|Pattern)\s*:\s*', '', heading).strip()
        body = ' '.join(body_lines)
        # Strip "Body:" prefix from body text
        body = re.sub(r'^(?:Body|Text|Content)\s*:\s*', '', body).strip()

        # Truncate body at word boundary (limits match slide layout capacity)
        body = _truncate_words(body, 200)

        # Split heading into before/highlight/after
        before, highlight, after = _split_heading(heading)

        if i == 0 or 'hook' in title:
            content['hook'] = {
                'before': before, 'highlight': highlight, 'after': after,
                'body': _truncate_words(body, 80),
            }
        elif i == len(slides) - 1 or 'when to use' in title or 'closing' in title:
            content['payoff'] = {
                'before': before, 'highlight': highlight, 'after': after,
                'body_before': 'Build better prompts with',
                'body_highlight': 'Prompt Optimizer',
                'body_after': '- link in bio',
            }
        else:
            step_num = f"0{technique_idx}" if technique_idx < 10 else str(technique_idx)
            key = f'technique_{technique_idx}'
            content[key] = {
                'before': before, 'highlight': highlight, 'after': after,
                'body': body,
                'step_number': step_num,
            }
            technique_idx += 1

    return content


def _truncate_words(text, max_chars):
    """Truncate text at a word boundary, never mid-word."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Find last space
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.5:
        truncated = truncated[:last_space]
    # Remove trailing punctuation fragments
    return truncated.rstrip('.,;:- ') + '.'


def _md_to_prompt_drop_yaml(md_text):
    """Parse prompt-drop markdown into cover/step_N/closing content YAML."""
    slides_match = re.search(r'## Slides\s*\n(.*?)(?=\n## [^#]|\Z)', md_text, re.DOTALL)
    if not slides_match:
        # Single image: extract from ## Image Content
        img_match = re.search(r'## Image Content\n\n?(.+?)(?=\n## |\Z)', md_text, re.DOTALL)
        if not img_match:
            return {}
        text = img_match.group(1).strip()
        before, highlight, after = _split_heading(text[:50])
        return {
            'cover': {'before': before, 'highlight': highlight, 'after': after, 'body': ''},
            'closing': {'before': 'Save this', 'highlight': 'prompt', 'after': '',
                        'body_before': 'Build yours with', 'body_highlight': 'Prompt Optimizer', 'body_after': ''},
        }

    slide_pattern = r'### Slide \d+\s*[-\u2013\u2014,:]\s*(.+?)\n(.*?)(?=### Slide|\Z)'
    slides = list(re.finditer(slide_pattern, slides_match.group(1), re.DOTALL))
    content = {}
    step_idx = 1

    for i, m in enumerate(slides):
        title = m.group(1).strip().lower()
        body_text = m.group(2).strip()
        bold_lines = re.findall(r'\*\*(.+?)\*\*', body_text)
        plain_lines = re.sub(r'\*\*.*?\*\*\s*', '', body_text).strip()
        plain_lines = [l.strip() for l in plain_lines.split('\n') if l.strip()]

        heading = bold_lines[0] if bold_lines else title
        body = ' '.join(plain_lines)
        before, highlight, after = _split_heading(heading)

        if i == 0:
            content['cover'] = {'before': before, 'highlight': highlight, 'after': after, 'body': body[:80]}
        elif i == len(slides) - 1:
            content['closing'] = {
                'before': before, 'highlight': highlight, 'after': after,
                'body_before': 'Bookmark this and build yours with',
                'body_highlight': 'Prompt Optimizer',
                'body_after': '',
            }
        else:
            content[f'step_{step_idx}'] = {'before': before, 'highlight': highlight, 'after': after, 'body': body[:120]}
            step_idx += 1

    return content


def _split_heading(text):
    """
    Split a heading string into before/highlight/after parts.
    Picks 1-2 key words to highlight with the red background.
    """
    text = text.strip().strip('"').strip("'")
    words = text.split()

    if len(words) <= 2:
        return '', text, ''

    # If there are quoted words, use those as highlight
    quoted = re.search(r'"([^"]+)"', text)
    if quoted:
        idx = text.index(quoted.group(0))
        return text[:idx].strip(), quoted.group(1), text[idx + len(quoted.group(0)):].strip()

    # Skip filler words for highlight: find the most meaningful 1-2 word chunk
    fillers = {'the', 'a', 'an', 'is', 'are', 'was', 'and', 'or', 'to', 'for',
               'in', 'on', 'at', 'of', 'with', 'your', 'you', 'it', 'its', 'not'}

    # Strategy: highlight the last noun/verb phrase (1-2 words), keep rest as before/after
    # Find the best 1-2 word highlight starting from the end
    best_start = max(0, len(words) - 2)
    for j in range(len(words) - 1, 0, -1):
        if words[j].lower() not in fillers and len(words[j]) > 2:
            best_start = max(0, j - 1) if j > 0 and words[j-1].lower() not in fillers else j
            break

    best_end = min(best_start + 2, len(words))

    before = ' '.join(words[:best_start])
    highlight = ' '.join(words[best_start:best_end])
    after = ' '.join(words[best_end:])

    return before, highlight, after


def _run_generation_full(job_id, params):
    """Full generation for complex categories (autopsy, prompt-pattern, etc.)."""
    try:
        platform = params["platform"]
        category = params["category"]
        topic = params["topic"]
        icp = params.get("icp", "solo-builder")
        slug = _slugify(topic)
        today = datetime.now().strftime("%Y-%m-%d")

        with job_lock:
            jobs[job_id]["progress"] = "Reading config files..."

        with job_lock:
            jobs[job_id]["progress"] = "Generating content with Claude..."

        claude_prompt = _build_claude_prompt(platform, category, topic, icp, today)

        result = subprocess.run(
            ["claude", "-p", claude_prompt, "--output-format", "text", "--max-turns", "1"],
            capture_output=True, text=True, timeout=180, cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = result.stderr or "Claude CLI returned non-zero exit code"
            return

        output_text = result.stdout.strip()
        # Strip em dashes - never allowed in post copy
        output_text = output_text.replace('\u2014', ',').replace('\u2013', ',')

        # Save to output file
        output_file = _make_output_file(platform, category, slug)
        output_file.write_text(output_text)
        rel_path = str(output_file.relative_to(OUTPUT_DIR))
        # Derive actual slug from filename (may have -2, -3 suffix)
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", output_file.stem)

        # Check if autopsy needs user input
        if category == "autopsy" and "[AWAITING_OPTIMIZED_PROMPT]" in output_text:
            with job_lock:
                jobs[job_id]["status"] = "awaiting_input"
                jobs[job_id]["progress"] = "Please provide the optimized prompt from Prompt Optimizer"
                jobs[job_id]["output_path"] = rel_path
                jobs[job_id]["slug"] = slug
            return

        # Render slides
        with job_lock:
            jobs[job_id]["progress"] = "Rendering slides..."
            jobs[job_id]["slug"] = slug

        template_yaml = PROJECT_ROOT / "templates" / f"{category}.yaml"

        # For categories with structured templates, convert markdown to content YAML
        content_dict, needs_yaml = _md_to_content_yaml(output_text, category)
        if needs_yaml and content_dict:
            content_yaml_path = output_file.with_suffix(".content.yaml")
            content_yaml_path.write_text(yaml.dump(content_dict, default_flow_style=False, allow_unicode=True))
            render_source = content_yaml_path
        else:
            render_source = output_file

        success, warning = _render_slides(category, template_yaml, render_source, slug)
        if warning:
            with job_lock:
                jobs[job_id]["render_warning"] = warning

        with job_lock:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = "Done!"
            jobs[job_id]["output_path"] = rel_path
            jobs[job_id]["slug"] = slug
            slides_path = SLIDES_DIR / slug
            if slides_path.exists():
                jobs[job_id]["slides_dir"] = str(slides_path.relative_to(PROJECT_ROOT))

    except subprocess.TimeoutExpired:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "Generation timed out (180s limit)"
    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)


def _continue_generation(job_id, optimized_prompt):
    """Resume autopsy generation after user provides optimized prompt."""
    try:
        job = jobs[job_id]
        rel_path = job["output_path"]
        slug = job["slug"]
        full_path = OUTPUT_DIR / rel_path

        with job_lock:
            jobs[job_id]["status"] = "generating"
            jobs[job_id]["progress"] = "Inserting optimized prompt..."

        # Replace placeholder
        text = full_path.read_text()
        text = text.replace("[AWAITING_OPTIMIZED_PROMPT]", optimized_prompt)
        full_path.write_text(text)

        # Re-render slides
        with job_lock:
            jobs[job_id]["progress"] = "Rendering slides..."

        category = job["params"]["category"]
        template_yaml = PROJECT_ROOT / "templates" / f"{category}.yaml"
        if template_yaml.exists():
            subprocess.run(
                ["python3", str(PROJECT_ROOT / "scripts" / "render_carousel.py"),
                 str(template_yaml), str(full_path), slug],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(PROJECT_ROOT),
            )

        with job_lock:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = "Done!"
            slides_path = SLIDES_DIR / slug
            if slides_path.exists():
                jobs[job_id]["slides_dir"] = str(slides_path.relative_to(PROJECT_ROOT))

    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)


# ── Routes: Pages ────────────────────────────────────────────────────

@app.route("/")
def index():
    posts = scan_posts()
    return render_template("index.html", posts=posts)


@app.route("/generate")
def generate_page():
    return render_template("generate.html")


@app.route("/preview/<path:rel_path>")
def preview_page(rel_path):
    post = parse_post(rel_path)
    if not post:
        return redirect(url_for("index"))
    return render_template("preview.html", post=post)


@app.route("/schedule/<path:rel_path>")
def schedule_page(rel_path):
    post = parse_post(rel_path)
    if not post:
        return redirect(url_for("index"))
    return render_template("schedule.html", post=post)


# ── Routes: API ──────────────────────────────────────────────────────

@app.route("/api/platforms")
def api_platforms():
    platforms = scan_platforms()
    result = []
    for pid, pdata in platforms.items():
        result.append({
            "id": pid,
            "name": pdata.get("name", pid),
        })
    return jsonify(result)


@app.route("/api/categories/<platform>")
def api_categories(platform):
    platforms = scan_platforms()
    pdata = platforms.get(platform, {})
    categories = pdata.get("categories", {})
    result = []
    for cid, cdata in categories.items():
        result.append({
            "id": cid,
            "name": cdata.get("name", cid),
            "format": cdata.get("format", ""),
            "frequency": cdata.get("frequency", ""),
            "description": cdata.get("description", "").strip(),
            "slot": cdata.get("slot", ""),
        })
    return jsonify(result)


@app.route("/api/topics/<platform>/<category>")
def api_topics(platform, category):
    banks = parse_content_bank()
    entries = banks.get(category, [])

    # For user-story, always show custom input
    allows_custom = True
    if category == "user-story":
        return jsonify({"topics": [], "allows_custom": True})

    import random
    if len(entries) > 4:
        selected = random.sample(entries, 4)
    else:
        selected = entries

    return jsonify({"topics": selected, "allows_custom": allows_custom})


@app.route("/api/icps")
def api_icps():
    icps = scan_icps()
    result = []
    for iid, idata in icps.items():
        result.append({
            "id": iid,
            "name": idata.get("name", iid),
            "description": idata.get("description", "").strip(),
        })
    return jsonify(result)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    platform = data.get("platform", "instagram")
    category = data.get("category")
    topic = data.get("topic")
    icp = data.get("icp", "solo-builder")

    if not category or not topic:
        return jsonify({"error": "category and topic are required"}), 400

    variant = data.get("variant")  # "fact_a" or "fact_b" for did-you-know
    topic_data = data.get("topic_data", {})  # Full content bank entry

    job_id = str(uuid.uuid4())
    params = {"platform": platform, "category": category, "topic": topic, "icp": icp}
    if variant:
        params["variant"] = variant
    if topic_data:
        params["topic_data"] = topic_data

    with job_lock:
        jobs[job_id] = {
            "status": "generating",
            "progress": "Starting...",
            "output_path": None,
            "slides_dir": None,
            "slug": None,
            "error": None,
            "params": params,
        }

    # Route to instant or full generation
    if category in INSTANT_RENDER_CATEGORIES and topic_data:
        target = _run_generation_instant
    else:
        target = _run_generation_full

    thread = threading.Thread(target=target, args=(job_id, params), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/generate/<job_id>/status")
def api_generate_status(job_id):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/generate/<job_id>/continue", methods=["POST"])
def api_generate_continue(job_id):
    with job_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "awaiting_input":
        return jsonify({"error": "Job is not awaiting input"}), 400

    data = request.get_json()
    optimized_prompt = data.get("optimized_prompt", "")
    if not optimized_prompt:
        return jsonify({"error": "optimized_prompt is required"}), 400

    thread = threading.Thread(
        target=_continue_generation, args=(job_id, optimized_prompt), daemon=True
    )
    thread.start()

    with job_lock:
        jobs[job_id]["status"] = "generating"
        jobs[job_id]["progress"] = "Resuming..."

    return jsonify({"status": "resumed"})


@app.route("/api/post/<path:rel_path>")
def api_post(rel_path):
    post = parse_post(rel_path)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    return jsonify(post)


@app.route("/api/delete", methods=["POST"])
def api_delete():
    import shutil
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    rel_path = data.get("path")
    if not rel_path:
        return jsonify({"error": "path is required"}), 400

    full_path = OUTPUT_DIR / rel_path
    if not full_path.exists():
        return jsonify({"error": "File not found"}), 404

    # Derive slug and delete slide images too
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", full_path.stem)
    slides_path = SLIDES_DIR / slug

    # Delete the markdown file (and any .content.yaml companion)
    full_path.unlink()
    content_yaml = full_path.with_suffix(".content.yaml")
    if content_yaml.exists():
        content_yaml.unlink()

    # Delete generated slides directory
    if slides_path.exists():
        shutil.rmtree(slides_path)

    return jsonify({"success": True, "deleted": rel_path, "slides_deleted": slides_path.exists()})


@app.route("/api/schedule", methods=["POST"])
def api_schedule():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    md_path = data.get("markdown_path")
    schedule_dt = data.get("datetime")
    mode = data.get("mode", "schedule")

    if not md_path:
        return jsonify({"error": "markdown_path is required"}), 400

    full_path = OUTPUT_DIR / md_path
    if not full_path.exists():
        return jsonify({"error": "File not found"}), 404

    cmd = ["python3", str(PROJECT_ROOT / "scripts" / "schedule_post.py"), str(full_path)]

    if mode == "now":
        # Use --schedule with 2 min delay instead of --now
        # Buffer needs time to process image assets before publishing
        from datetime import timedelta
        publish_at = datetime.now() + timedelta(minutes=2)
        cmd.extend(["--schedule", publish_at.strftime("%Y-%m-%d %H:%M")])
    elif mode == "draft":
        cmd.append("--queue")
    else:
        if not schedule_dt:
            return jsonify({"error": "datetime is required for schedule mode"}), 400
        cmd.extend(["--schedule", schedule_dt])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            return jsonify({"error": result.stderr or "Schedule failed", "stdout": result.stdout}), 500
        return jsonify({"success": True, "output": result.stdout})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Scheduling timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Serve generated slide images ─────────────────────────────────────

@app.route("/slides/<path:filepath>")
def serve_slide(filepath):
    return send_from_directory(str(SLIDES_DIR), filepath)


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
