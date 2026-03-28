"""
Flask web UI for the marketing content pipeline.

Walks the user through: platform -> category -> topic -> generate -> preview -> schedule.
Single user, localhost only.

Usage:
    cd web && python3 app.py
    # or from project root:
    python3 web/app.py
"""

import json
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

import yaml

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from process_infographic import process_infographic
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
                cell_val = cells[i].strip() if i < len(cells) else ""
                # Only strip surrounding quotes if the cell is fully quoted
                if len(cell_val) >= 2 and cell_val[0] == '"' and cell_val[-1] == '"':
                    cell_val = cell_val[1:-1]
                # Strip em dashes — never allowed in post text or captions
                cell_val = cell_val.replace('\u2014', ',').replace('\u2013', ',')
                entry[col_name] = cell_val
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

        # Find slides — infographics store image path in frontmatter
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", md_file.stem)
        infographic_image = fm.get("infographic_image")
        if infographic_image:
            img_path = PROJECT_ROOT / infographic_image
            slide_images = [img_path] if img_path.exists() else []
            thumbnail = str(img_path.relative_to(SLIDES_DIR)) if slide_images else None
        else:
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

    # Slide images — infographics store image path in frontmatter
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", Path(rel_path).stem)
    infographic_image = fm.get("infographic_image")
    slide_images = []
    if infographic_image:
        img_path = PROJECT_ROOT / infographic_image
        if img_path.exists():
            slide_images = [str(img_path.relative_to(SLIDES_DIR))]
    else:
        slides_path = _find_slides_dir(slug)
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

def _yaml_quote(text):
    """Safely quote a string for YAML frontmatter values."""
    # Use single quotes and escape internal single quotes by doubling them
    escaped = str(text).replace("'", "''")
    return f"'{escaped}'"


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
INSTANT_RENDER_CATEGORIES = {"daily-prompt"}


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


def _run_claude(prompt, timeout=180):
    """Run Claude CLI from project directory with skills enabled. Returns (success, stdout, stderr)."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "5"],
        capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT_ROOT),
    )
    stdout = result.stdout.strip()
    # Strip code fences Claude sometimes wraps output in
    stdout = re.sub(r'^```(?:markdown)?\s*\n', '', stdout)
    stdout = re.sub(r'\n```\s*$', '', stdout)
    # Strip any leading non-frontmatter text before ---
    if '\n---\n' in stdout and not stdout.startswith('---'):
        idx = stdout.index('---')
        stdout = stdout[idx:]
    # Strip em dashes globally
    stdout = stdout.replace('\u2014', ',').replace('\u2013', ',')
    # Strip Claude's meta-commentary (character counts, explanations after the content)
    stdout = re.sub(r'\n\*\*Character count:\*\*.*$', '', stdout, flags=re.DOTALL)
    stdout = re.sub(r'\n\*\*Why this works:\*\*.*$', '', stdout, flags=re.DOTALL)
    stdout = re.sub(r'\n\*\*Heading breakdown.*$', '', stdout, flags=re.DOTALL)
    return result.returncode == 0, stdout.strip(), result.stderr.strip()


def _load_config_texts(platform, icp):
    """Load brand, platform, and ICP config texts."""
    brand_text = (CONFIG_DIR / "brand.yaml").read_text() if (CONFIG_DIR / "brand.yaml").exists() else ""
    platform_text = (CONFIG_DIR / "platforms" / f"{platform}.yaml").read_text() if (CONFIG_DIR / "platforms" / f"{platform}.yaml").exists() else ""
    icp_text = (CONFIG_DIR / "icps" / f"{icp}.yaml").read_text() if (CONFIG_DIR / "icps" / f"{icp}.yaml").exists() else ""
    return brand_text, platform_text, icp_text


def _build_post_text_prompt(platform, category, topic, icp, today):
    """Build prompt for Step 2: generate ONLY slide text using the post-text skill."""
    brand_text, platform_text, icp_text = _load_config_texts(platform, icp)
    prompt_path = PROMPTS_DIR / platform / f"{category}.md"
    if not prompt_path.exists():
        prompt_path = PROMPTS_DIR / "instagram" / f"{category}.md"
    prompt_text = prompt_path.read_text() if prompt_path.exists() else ""

    autopsy_note = ""
    if category == "autopsy":
        autopsy_note = "\n\nIMPORTANT: Generate everything EXCEPT the optimized prompt slide. Write [AWAITING_OPTIMIZED_PROMPT] as a placeholder for the optimized prompt."

    return f"""You are generating the SLIDE TEXT for a {category} Instagram post about: {topic}

Use the /post-text skill. Follow its rules for the {category} category exactly.

Target ICP: {icp}

Brand config:
---
{brand_text}
---

Platform config:
---
{platform_text}
---

ICP profile:
---
{icp_text}
---

Prompt template (follow this structure exactly):
---
{prompt_text}
---

IMPORTANT: Generate ONLY the slide content. Do NOT generate a caption, hashtags, or alt text.
Output raw markdown starting with YAML frontmatter, then # Title, then ## Slides with ### Slide N entries.

Use this frontmatter:
---
platform: {platform}
category: {category}
topic: {_yaml_quote(topic)}
icp: {icp}
date: {today}
status: draft
---
{autopsy_note}
"""


PLATFORM_CAPTION_NOTES = {
    "instagram": "Platform: Instagram. Use 'Link in bio' for the CTA. Hashtags: 5-10.",
    "twitter": (
        "Platform: X (Twitter). Max 280 characters for the caption. "
        "Weave the CTA naturally into the last sentence with the link: https://www.promptoptimizr.com/ "
        "Do NOT just append the URL. Do NOT say 'link in bio'. Hashtags: 0-2 max."
    ),
}


def _build_caption_prompt(platform, category, topic, icp, slide_content):
    """Build prompt for Step 3: generate ONLY caption using the caption-writer skill."""
    brand_text, _, icp_text = _load_config_texts(platform, icp)
    platform_note = PLATFORM_CAPTION_NOTES.get(platform, PLATFORM_CAPTION_NOTES["instagram"])

    return f"""You are writing the caption for a {category} post about: {topic}

{platform_note}

Use the /caption-writer skill. Follow its rules exactly, including the platform-specific adaptations for {platform}.

Target ICP: {icp}

Brand config:
---
{brand_text}
---

ICP profile:
---
{icp_text}
---

Here is the slide content that was generated for this post (use this as context for the caption):
---
{slide_content}
---

Output ONLY these three sections:

## Caption

[caption text]

## Hashtags

[hashtags]

## Alt Text

[alt text]
"""


def _run_caption_generation(job_id, platform, category, topic, icp, output_file, slide_content=""):
    """Generate caption/hashtags/alt text via Claude caption-writer skill, then update the markdown."""
    try:
        if not slide_content:
            slide_content = output_file.read_text()

        caption_prompt = _build_caption_prompt(platform, category, topic, icp, slide_content)
        ok, claude_output, err = _run_claude(caption_prompt)

        if not ok:
            with job_lock:
                jobs[job_id]["caption_status"] = "error"
                jobs[job_id]["caption_error"] = err or "Claude CLI failed"
            return

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
            # Strip em dashes — never allowed in post text
            fact_text = fact_text.replace('\u2014', ',').replace('\u2013', ',')
            detail_text = detail_text.replace('\u2014', ',').replace('\u2013', ',')
            # Combine fact + detail for the slide text (max 150 chars to fit in phone frame)
            slide_fact = f"{fact_text}. {detail_text}" if detail_text else fact_text
            if len(slide_fact) > 150:
                slide_fact = _truncate_words(slide_fact, 150)
            variant_key = variant or "fact_a"
            content_data = {variant_key: {"fact": slide_fact}}
        elif category == "daily-prompt":
            optimized = params.get("optimized_prompt", topic)
            raw = params.get("raw_prompt", "")
            content_data = {"prompt": {"prompt": optimized}}
        else:
            content_data = {}

        # Write content YAML
        output_file = _make_output_file(platform, category, slug)
        content_yaml_path = output_file.with_suffix(".content.yaml")
        content_yaml_path.write_text(yaml.dump(content_data, default_flow_style=False, allow_unicode=True))

        # Write initial markdown (slide content, no caption yet)
        if category == "daily-prompt":
            optimized = params.get("optimized_prompt", topic)
            raw = params.get("raw_prompt", "")
            md_text = f"""---
platform: {platform}
category: {category}
topic: {_yaml_quote(topic)}
icp: {icp}
date: {today}
status: draft
---

# Daily Prompt: {slug}

## Image Content

**Optimized Prompt:** {optimized}

## Raw Prompt

{raw}
"""
        else:
            md_text = f"""---
platform: {platform}
category: {category}
topic: {_yaml_quote(topic)}
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
        # For daily-prompt, pass both raw and optimized prompts as the topic
        # so the caption can contrast them
        if category == "daily-prompt":
            caption_topic = f"Raw prompt: {params.get('raw_prompt', '')}\n\nOptimized prompt: {params.get('optimized_prompt', '')}"
        else:
            caption_topic = topic

        caption_thread = threading.Thread(
            target=_run_caption_generation,
            args=(job_id, platform, category, caption_topic, icp, output_file),
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
    if category == "user-story":
        return _md_to_user_story_yaml(md_text), True
    if category == "did-you-know":
        return _md_to_dyk_yaml(md_text), True
    # autopsy: uses markdown-based rendering in render_carousel.py
    return None, False


def _md_to_prompt_pattern_yaml(md_text):
    """Parse prompt-pattern markdown into hook/technique_N/payoff content YAML."""
    # Strip code fences if Claude wrapped the output
    md_text = re.sub(r'```(?:markdown)?\s*\n', '', md_text)
    md_text = re.sub(r'\n```', '', md_text)

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

        # Detect which format Claude used for this slide:
        # Format A: **Heading before:** / **Heading highlight:** / **Heading after:** / **Body:**
        # Format B: **Before:** / **Highlight:** / **After:** / **Body:**  (heading field labels)
        # Format C: **Heading:** value / **Body:** value
        # Format D: **Bold heading**\nBody text (unlabeled)

        h_highlight_match = re.search(r'\*\*(?:Heading )?highlight:\*\* *(.*)', body_text, re.IGNORECASE)
        body_match = re.search(r'\*\*Body\s*:\*\*\s*(.+?)(?=\n\*\*|\n\n|\Z)', body_text, re.DOTALL)

        if h_highlight_match:
            # Format A or B: heading split into before/highlight/after fields
            h_before_match = re.search(r'\*\*(?:Heading )?before:\*\* *(.*)', body_text, re.IGNORECASE)
            h_after_match = re.search(r'\*\*(?:Heading )?after:\*\* *(.*)', body_text, re.IGNORECASE)
            before_word = h_before_match.group(1).strip() if h_before_match else ''
            highlight_word = h_highlight_match.group(1).strip()
            after_word = h_after_match.group(1).strip() if h_after_match else ''
            body_only = body_match.group(1).strip() if body_match else ''
            _presplit = (before_word, highlight_word, after_word)
        else:
            _presplit = None

            # Format C: **Heading:** value
            heading_match = re.search(r'\*\*(?:Heading|Title|Hook|Pattern)\s*:\*\*\s*(.+?)(?=\n|$)', body_text)

            if heading_match:
                bold_lines = [heading_match.group(1).strip()]
                body_only = body_match.group(1).strip() if body_match else ''
            else:
                # Format D: unlabeled — first bold text is heading, rest is body
                all_bold = re.findall(r'\*\*(.+?)\*\*', body_text)
                bold_lines = [b for b in all_bold if not re.match(r'^(?:Body|Text|Heading|Before|After|Highlight)\s*:?', b, re.IGNORECASE)]
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

        if _presplit:
            before, highlight, after = _presplit
            body = ' '.join(body_lines)
            body = re.sub(r'^(?:Body|Text|Content)\s*:\s*', '', body).strip()
        else:
            heading = bold_lines[0] if bold_lines else m.group(1).strip()
            heading = re.sub(r'^(?:Heading|Title|Hook|Pattern)\s*:\s*', '', heading).strip()
            body = ' '.join(body_lines)
            body = re.sub(r'^(?:Body|Text|Content)\s*:\s*', '', body).strip()
            before, highlight, after = _split_heading(heading)

        # Truncate body at word boundary (limits match slide layout capacity)
        body = _truncate_words(body, 200)

        if i == 0 or 'hook' in title:
            content['hook'] = {
                'before': before, 'highlight': highlight, 'after': after,
                'body': _truncate_words(body, 80),
            }
        elif i == len(slides) - 1 or 'when to use' in title or 'closing' in title:
            content['payoff'] = {
                'before': 'Save this', 'highlight': 'Post', 'after': '',
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
    """Truncate text at the last complete sentence within the character limit."""
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]

    # Find the last sentence-ending punctuation (. ! ?) NOT inside quotes
    # Walk backwards, tracking quote depth
    in_quote = False
    last_sentence_end = -1
    for i in range(len(truncated) - 1, 0, -1):
        if truncated[i] == '"':
            in_quote = not in_quote
        if not in_quote and truncated[i] in '.!?' and i > 0 and truncated[i - 1].isalpha():
            # Check it's followed by space or end of string
            if i == len(truncated) - 1 or truncated[i + 1] == ' ' or truncated[i + 1] == '"':
                last_sentence_end = i + 1
                break

    if last_sentence_end > max_chars * 0.3:
        return truncated[:last_sentence_end].strip()

    # Fallback: cut at last space
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.5:
        truncated = truncated[:last_space]
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


def _md_to_dyk_yaml(md_text, variant="fact_a"):
    """Parse did-you-know markdown into fact_a or fact_b content YAML."""
    # Strip code fences
    md_text = re.sub(r'```(?:markdown)?\s*\n', '', md_text)
    md_text = re.sub(r'\n```', '', md_text)

    # Try to extract from ## Image Content section
    fact_text = ""
    img_match = re.search(r'## Image Content\n\n?(.+?)(?=\n## |\n\n\*\*|\Z)', md_text, re.DOTALL)
    if img_match:
        raw = img_match.group(1).strip()
        # Strip **Fact:** label if present
        raw = re.sub(r'^\*\*Fact:\*\*\s*', '', raw).strip()
        # Take only first paragraph (stop at blank line or **label**)
        raw = raw.split('\n\n')[0].strip()
        # Strip markdown formatting
        raw = re.sub(r'\*\*([^*]*)\*\*', r'\1', raw)
        raw = raw.replace('`', '')
        fact_text = raw

    # Fallback: try ## Slides section
    if not fact_text:
        slide_match = re.search(r'### Slide 1.*?\n(.*?)(?=### Slide|\n## |\Z)', md_text, re.DOTALL)
        if slide_match:
            raw = slide_match.group(1).strip()
            # Strip labels
            raw = re.sub(r'\*\*(?:Fact|Body|Text)\s*:\*\*\s*', '', raw).strip()
            raw = re.sub(r'\*\*([^*]*)\*\*', r'\1', raw)
            raw = raw.replace('`', '')
            fact_text = raw

    # Strip em dashes
    fact_text = fact_text.replace('\u2014', ',').replace('\u2013', ',')

    # Enforce 150 char limit
    if len(fact_text) > 150:
        fact_text = _truncate_words(fact_text, 150)

    # Detect variant from frontmatter or default
    variant_match = re.search(r'variant:\s*(\w+)', md_text)
    if variant_match:
        variant = variant_match.group(1)

    return {variant: {"fact": fact_text}}


def _md_to_user_story_yaml(md_text):
    """Parse user-story markdown into hook/old_way/the_switch/result/payoff/cta content YAML."""
    slides_match = re.search(r'## Slides\s*\n(.*?)(?=\n## [^#]|\Z)', md_text, re.DOTALL)
    if not slides_match:
        return {}

    slide_pattern = r'### Slide \d+\s*[-\u2013\u2014,:]\s*(.+?)\n(.*?)(?=### Slide|\Z)'
    slides = list(re.finditer(slide_pattern, slides_match.group(1), re.DOTALL))
    if not slides:
        return {}

    # Slide type mapping based on title keywords
    TYPE_MAP = [
        (["hook", "problem", "struggle"], "hook"),
        (["old way", "before", "was doing", "regenerate", "copy-paste"], "old_way"),
        (["switch", "changed", "click", "optimiz"], "the_switch"),
        (["result", "night and day", "first try", "outcome"], "result"),
        (["takeaway", "lesson", "payoff", "wasn't", "wasn"], "payoff"),
        (["cta", "try it", "link in bio"], "cta"),
    ]

    content = {}

    for i, m in enumerate(slides):
        title = m.group(1).strip()
        body_text = m.group(2).strip()
        title_lower = title.lower()

        # Determine slide type from title
        slide_type = None
        for keywords, stype in TYPE_MAP:
            if any(kw in title_lower for kw in keywords):
                slide_type = stype
                break

        # Fallback based on position
        if not slide_type:
            positional = ["hook", "old_way", "the_switch", "result", "payoff", "cta"]
            slide_type = positional[i] if i < len(positional) else "payoff"

        # Parse **Heading:** and **Body:** labels if present
        heading_match = re.search(r'\*\*(?:Heading|Title)\s*:\*\*\s*(.+?)(?=\n|$)', body_text)
        body_match = re.search(r'\*\*(?:Body|Text)\s*:\*\*\s*(.+?)(?=\n\*\*|\Z)', body_text, re.DOTALL)
        quote_match = re.search(r'"([^"]{10,})"', body_text)

        if heading_match:
            heading = heading_match.group(1).strip()
            body = body_match.group(1).strip() if body_match else ''
        else:
            # No labels — split first line as heading, rest as body
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            # Remove markdown formatting
            lines = [re.sub(r'\*\*([^*]+)\*\*', r'\1', l) for l in lines]
            lines = [l.replace('`', '') for l in lines]

            if slide_type == "hook":
                # Hook: first line is the problem, rest is hook_line
                heading = lines[0] if lines else title
                body = ' '.join(lines[1:]) if len(lines) > 1 else ''
            else:
                heading = title
                body = ' '.join(lines)

        # Clean markdown artifacts
        heading = re.sub(r'\*\*([^*]*)\*\*', r'\1', heading).strip()
        heading = heading.replace('`', '').replace('#', '').strip()
        body = re.sub(r'\*\*([^*]*)\*\*', r'\1', body).strip()
        body = body.replace('`', '').replace('#', '').strip()

        # Build content for each slide type
        if slide_type == "hook":
            # Hook title is 118px font in ~600px wide area — max ~30 chars to avoid word breaks
            problem_text = heading
            if len(problem_text) > 30:
                # Try to cut at a sentence boundary
                for punct in ['.', '!', '?']:
                    idx = problem_text[:30].rfind(punct)
                    if idx > 10:
                        problem_text = problem_text[:idx + 1]
                        break
                else:
                    problem_text = _truncate_words(problem_text, 30)
            content["hook"] = {
                "problem": problem_text,
                "hook_line": _truncate_words(body, 60) if body else "",
            }
        elif slide_type == "cta":
            content["cta"] = {
                "cta_headline": "Try it for Free",
                "cta_url": "promptoptimizr.com",
                "cta_sub": "link in bio",
            }
        else:
            placeholders = {
                "heading": heading.upper() if len(heading) < 40 else heading,
                "body": _truncate_words(body, 150),
            }
            if slide_type == "result" and quote_match:
                placeholders["quote"] = _truncate_words(quote_match.group(1), 80)
            content[slide_type] = placeholders

    # Ensure CTA always exists
    if "cta" not in content:
        content["cta"] = {
            "cta_headline": "Try it for Free",
            "cta_url": "promptoptimizr.com",
            "cta_sub": "link in bio",
        }

    return content


def _run_generation_phased(job_id, params):
    """Phased generation: Step 2 (post-text skill) → render → Step 3 (caption-writer skill)."""
    try:
        platform = params["platform"]
        category = params["category"]
        topic = params["topic"]
        icp = params.get("icp", "solo-builder")
        slug = _slugify(topic)
        today = datetime.now().strftime("%Y-%m-%d")

        # ── Phase 1: Generate slide text via post-text skill ──
        with job_lock:
            jobs[job_id]["progress"] = "Generating slide content (post-text skill)..."

        post_text_prompt = _build_post_text_prompt(platform, category, topic, icp, today)
        ok, output_text, err = _run_claude(post_text_prompt)

        if not ok:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = err or "Claude CLI failed during slide text generation"
            return

        # Save to output file
        output_file = _make_output_file(platform, category, slug)
        output_file.write_text(output_text)
        rel_path = str(output_file.relative_to(OUTPUT_DIR))
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", output_file.stem)

        # Check if autopsy needs user input before rendering
        if category == "autopsy" and "[AWAITING_OPTIMIZED_PROMPT]" in output_text:
            with job_lock:
                jobs[job_id]["status"] = "awaiting_input"
                jobs[job_id]["progress"] = "Please provide the optimized prompt from Prompt Optimizer"
                jobs[job_id]["output_path"] = rel_path
                jobs[job_id]["slug"] = slug
            return

        # ── Phase 2: Render slides ──
        with job_lock:
            jobs[job_id]["progress"] = "Rendering slides..."
            jobs[job_id]["slug"] = slug

        template_yaml = PROJECT_ROOT / "templates" / f"{category}.yaml"

        variant = params.get("variant")
        content_dict, needs_yaml = _md_to_content_yaml(output_text, category)
        # For DYK: ensure the content uses the selected variant key
        if category == "did-you-know" and content_dict and variant:
            # Re-key the content under the correct variant
            fact_text = ""
            for k in list(content_dict.keys()):
                if "fact" in content_dict[k]:
                    fact_text = content_dict[k]["fact"]
                    break
            if fact_text:
                content_dict = {variant: {"fact": fact_text}}
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

        # Mark complete (slides ready for preview)
        with job_lock:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = "Done! Writing caption in background..."
            jobs[job_id]["output_path"] = rel_path
            jobs[job_id]["caption_status"] = "generating"
            slides_path = SLIDES_DIR / slug
            if slides_path.exists():
                jobs[job_id]["slides_dir"] = str(slides_path.relative_to(PROJECT_ROOT))

        # ── Phase 3: Generate caption via caption-writer skill (background) ──
        caption_thread = threading.Thread(
            target=_run_caption_generation,
            args=(job_id, platform, category, topic, icp, output_file, output_text),
            daemon=True,
        )
        caption_thread.start()

    except subprocess.TimeoutExpired:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "Generation timed out"
    except Exception as e:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)


NOTEBOOK_ID = "57639ed8-99e9-47c0-b82d-6d9443f88b51"

INFOGRAPHIC_STYLE_MAP = {
    "cheat_sheet": "professional",
    "comparison": "editorial",
    "framework": "instructional",
    "data_insight": "editorial",
}

RESEARCH_QUESTION_TEMPLATES = {
    "cheat_sheet": "What are the 3-7 most important rules for {topic}? Give only the top points, each with a one-sentence explanation.",
    "comparison": "Compare the key aspects of {topic}. List 3-5 main differences, each with a one-sentence explanation.",
    "framework": "What is the recommended framework for {topic}? Break it into 3-5 clear stages with a one-sentence explanation each.",
    "data_insight": "What are the 3-5 most important data points about {topic}? Give each with a one-sentence explanation.",
}

INFOGRAPHIC_INSTRUCTIONS = (
    "CRITICAL: Keep this infographic SIMPLE and READABLE. "
    "Use only 3-7 main points. Each point gets a bold heading and 2-3 lines of subtext maximum. "
    "Large, readable fonts throughout. No tables, no complex diagrams, no nested bullets. "
    "Clean layout with plenty of whitespace. Every word must be legible at phone screen size."
)


def _run_notebooklm_cmd(args, timeout=60):
    """Run a notebooklm CLI command and return (success, stdout, stderr)."""
    result = subprocess.run(
        ["notebooklm"] + args,
        capture_output=True, text=True, timeout=timeout,
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def _run_generation_infographic(job_id, params):
    """Full generation for infographic posts via NotebookLM + Claude caption."""
    try:
        platform = params["platform"]
        category = params["category"]
        topic = params["topic"]
        icp = params.get("icp", "solo-builder")
        topic_data = params.get("topic_data", {})
        slug = _slugify(topic_data.get("title", topic))
        today = datetime.now().strftime("%Y-%m-%d")

        infographic_type = topic_data.get("type", "cheat_sheet")
        style = INFOGRAPHIC_STYLE_MAP.get(infographic_type, "professional")

        # Create output file and slides directory
        output_file = _make_output_file(platform, category, slug)
        rel_path = str(output_file.relative_to(OUTPUT_DIR))
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", output_file.stem)

        slides_dir = SLIDES_DIR / slug
        slides_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1: Set NotebookLM context
        with job_lock:
            jobs[job_id]["progress"] = "Setting up NotebookLM..."
        ok, _, err = _run_notebooklm_cmd(["use", NOTEBOOK_ID])
        if not ok:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = f"Failed to set NotebookLM context: {err}"
            return

        # Phase 2: Research topic
        with job_lock:
            jobs[job_id]["progress"] = "Researching topic via NotebookLM..."
        question_template = RESEARCH_QUESTION_TEMPLATES.get(infographic_type, RESEARCH_QUESTION_TEMPLATES["cheat_sheet"])
        research_question = question_template.format(topic=topic)

        ok, research_stdout, err = _run_notebooklm_cmd(
            ["ask", research_question, "--json"], timeout=120
        )
        research_text = ""
        if ok and research_stdout:
            try:
                research_data = json.loads(research_stdout)
                research_text = research_data.get("answer", research_stdout)
            except json.JSONDecodeError:
                research_text = research_stdout

        # Phase 3: Generate infographic image
        with job_lock:
            jobs[job_id]["progress"] = "Generating infographic image (this may take a few minutes)..."
        ok, gen_stdout, err = _run_notebooklm_cmd(
            ["generate", "infographic", INFOGRAPHIC_INSTRUCTIONS,
             "--orientation", "square", "--detail", "concise",
             "--style", style, "--json"],
            timeout=60,
        )
        if not ok:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = f"Failed to start infographic generation: {err}"
            return

        artifact_id = None
        try:
            gen_data = json.loads(gen_stdout)
            artifact_id = gen_data.get("task_id") or gen_data.get("artifact_id") or gen_data.get("id")
        except json.JSONDecodeError:
            pass

        if not artifact_id:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = f"Could not parse artifact ID from NotebookLM: {gen_stdout}"
            return

        # Phase 4: Wait for generation to complete
        with job_lock:
            jobs[job_id]["progress"] = "Waiting for infographic generation (this may take 5-15 minutes)..."
        ok, _, err = _run_notebooklm_cmd(
            ["artifact", "wait", artifact_id, "--timeout", "600"],
            timeout=660,
        )
        if not ok:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = f"Infographic generation timed out or failed: {err}"
            return

        # Phase 5: Download image
        with job_lock:
            jobs[job_id]["progress"] = "Downloading infographic..."
        image_path = slides_dir / "infographic.png"
        ok, _, err = _run_notebooklm_cmd(
            ["download", "infographic", str(image_path)],
            timeout=60,
        )
        if not ok or not image_path.exists():
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = f"Failed to download infographic: {err}"
            return

        # Phase 6: Post-process (watermark removal, resize to 1080px)
        with job_lock:
            jobs[job_id]["progress"] = "Post-processing image..."
        try:
            process_infographic(str(image_path))
        except Exception as e:
            with job_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = f"Image post-processing failed: {e}"
            return

        # Determine final image path (process_infographic converts to .jpg)
        final_image = slides_dir / "infographic.jpg"
        if not final_image.exists():
            final_image = image_path  # fallback to .png if conversion didn't happen
        infographic_image_rel = str(final_image.relative_to(PROJECT_ROOT))

        # Phase 7: Write initial markdown (without caption, added by background thread)
        with job_lock:
            jobs[job_id]["progress"] = "Generating caption with Claude..."
        md_text = f"""---
platform: {platform}
category: infographic
topic: {_yaml_quote(topic)}
icp: {icp}
date: {today}
status: draft
infographic_image: {infographic_image_rel}
notebooklm_notebook: {NOTEBOOK_ID}
---

# {topic_data.get('title', topic)}

## Research Notes

{research_text}
"""
        output_file.write_text(md_text)

        # Mark as complete (image is ready for preview)
        with job_lock:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = "Done! Generating caption in background..."
            jobs[job_id]["output_path"] = rel_path
            jobs[job_id]["slug"] = slug
            jobs[job_id]["caption_status"] = "generating"
            jobs[job_id]["slides_dir"] = str(slides_dir.relative_to(PROJECT_ROOT))

        # Phase 8: Generate caption in background thread
        caption_thread = threading.Thread(
            target=_run_caption_generation,
            args=(job_id, platform, category, topic, icp, output_file),
            daemon=True,
        )
        caption_thread.start()

    except subprocess.TimeoutExpired:
        with job_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "NotebookLM operation timed out"
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

        # Mark complete and generate caption in background
        with job_lock:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["progress"] = "Done! Writing caption in background..."
            jobs[job_id]["caption_status"] = "generating"
            slides_path = SLIDES_DIR / slug
            if slides_path.exists():
                jobs[job_id]["slides_dir"] = str(slides_path.relative_to(PROJECT_ROOT))

        # Phase 3: Caption via caption-writer skill
        params = job["params"]
        caption_thread = threading.Thread(
            target=_run_caption_generation,
            args=(job_id, params["platform"], params["category"], params["topic"],
                  params.get("icp", "solo-builder"), full_path, text),
            daemon=True,
        )
        caption_thread.start()

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
    # Load platform config for max_images (used by slide picker)
    platform = post.get("frontmatter", {}).get("platform", "instagram")
    platforms = scan_platforms()
    platform_config = platforms.get(platform, {})
    max_images = platform_config.get("max_images", 10)
    return render_template("schedule.html", post=post, max_images=max_images)


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


CATEGORY_FIELD_MAP = {
    "autopsy": {"fields": ["bad_prompt", "hook"], "example": '{"bad_prompt": "fix my code", "hook": "This wastes 90% of the model."}'},
    "did-you-know": {"fields": ["fact", "detail"], "example": '{"fact": "Claude uses XML, not Markdown", "detail": "Claude responds better to <task> tags"}'},
    "prompt-pattern": {"fields": ["pattern_name", "core_insight"], "example": '{"pattern_name": "Scope Narrowing", "core_insight": "Narrow scope = better output"}'},
    "infographic": {"fields": ["title", "type"], "example": '{"title": "The Prompt Checklist", "type": "cheat_sheet"}'},
    "user-story": {"fields": ["persona", "problem"], "example": '{"persona": "Solo dev building SaaS", "problem": "Spent 20 min per prompt"}'},
    "daily-prompt": {"fields": ["task"], "example": '{"task": "write a marketing plan"}'},
}


def _generate_topic_ideas(platform, category):
    """Generate fresh topic ideas via Claude using the post-text skill context."""
    import random as _random

    # Load category description from platform config
    platforms = scan_platforms()
    pdata = platforms.get(platform, {})
    cat_config = pdata.get("categories", {}).get(category, {})
    cat_description = cat_config.get("description", "").strip()
    cat_name = cat_config.get("name", category)

    # Get content bank examples for style reference
    banks = parse_content_bank()
    examples = banks.get(category, [])
    example_text = ""
    if examples:
        sample = _random.sample(examples, min(3, len(examples)))
        example_text = "Here are example topics for style reference (generate NEW ideas, do not copy these):\n"
        for ex in sample:
            example_text += f"  {json.dumps(ex)}\n"

    field_info = CATEGORY_FIELD_MAP.get(category, {"fields": ["topic"], "example": '{"topic": "example"}'})

    prompt = f"""Generate 6 original, fresh topic ideas for a "{cat_name}" Instagram post.

Category description: {cat_description}

{example_text}

For each idea, output a JSON object with these fields: {', '.join(field_info['fields'])}
Example format: {field_info['example']}

Output ONLY a JSON array of 6 objects. No markdown, no explanation, no code fences. Just the raw JSON array.
"""

    try:
        ok, stdout, err = _run_claude(prompt, timeout=60)
        if ok and stdout:
            # Try to extract JSON array from output
            json_match = re.search(r'\[.*\]', stdout, re.DOTALL)
            if json_match:
                ideas = json.loads(json_match.group())
                if isinstance(ideas, list) and len(ideas) > 0:
                    # Add IDs
                    for i, idea in enumerate(ideas):
                        idea["id"] = i + 1
                    return ideas
    except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception):
        pass

    return None  # Signal to fall back to content bank


@app.route("/api/topics/<platform>/<category>")
def api_topics(platform, category):
    import random

    # daily-prompt uses dual textareas, not topic cards
    if category == "daily-prompt":
        return jsonify({"topics": [], "allows_custom": True})

    # Try generating fresh ideas via Claude
    ideas = _generate_topic_ideas(platform, category)
    if ideas:
        return jsonify({"topics": ideas[:6], "allows_custom": True})

    # Fallback: sample from content bank
    banks = parse_content_bank()
    entries = banks.get(category, [])
    if len(entries) > 4:
        selected = random.sample(entries, 4)
    else:
        selected = entries

    return jsonify({"topics": selected, "allows_custom": True})


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
    raw_prompt = data.get("raw_prompt", "")
    optimized_prompt = data.get("optimized_prompt", "")

    job_id = str(uuid.uuid4())
    params = {"platform": platform, "category": category, "topic": topic, "icp": icp}
    if variant:
        params["variant"] = variant
    if topic_data:
        params["topic_data"] = topic_data
    if raw_prompt:
        params["raw_prompt"] = raw_prompt
    if optimized_prompt:
        params["optimized_prompt"] = optimized_prompt

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

    # Route to instant, infographic, or full generation
    if category in INSTANT_RENDER_CATEGORIES and (topic_data or category == "daily-prompt"):
        target = _run_generation_instant
    elif category == "infographic":
        target = _run_generation_infographic
    else:
        target = _run_generation_phased

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

    # Pass selected slides if provided (for Twitter 4-image limit)
    slides = data.get("slides")
    if slides:
        cmd.extend(["--slides", slides])

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


# ── Cross-post to another platform ───────────────────────────────────

@app.route("/api/crosspost", methods=["POST"])
def api_crosspost():
    """Create a cross-post: copy an existing post to another platform with a new caption."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    source_path = data.get("source_path")  # relative path under output/
    target_platform = data.get("target_platform", "twitter")
    selected_slides = data.get("slides")  # comma-separated 1-based indices (for carousel limit)

    if not source_path:
        return jsonify({"error": "source_path is required"}), 400

    source = parse_post(source_path)
    if not source:
        return jsonify({"error": "Source post not found"}), 404

    fm = source["frontmatter"]
    category = fm.get("category", "")
    topic = fm.get("topic", "")
    icp = fm.get("icp", "solo-builder")
    today = datetime.now().strftime("%Y-%m-%d")

    # Create the target output file
    output_file = _make_output_file(target_platform, category, source["slug"])

    # Read the source markdown and replace the platform in frontmatter
    source_full = OUTPUT_DIR / source_path
    source_text = source_full.read_text()

    # Replace platform in frontmatter
    target_text = re.sub(
        r"^(platform:\s*).*$",
        f"\\1{target_platform}",
        source_text,
        count=1,
        flags=re.MULTILINE,
    )

    # Remove old caption/hashtags/alt text (will be regenerated)
    target_text = re.sub(r"\n## Caption\n\n?.*?(?=\n## [^#]|\Z)", "", target_text, flags=re.DOTALL)
    target_text = re.sub(r"\n## Hashtags\n\n?.*?(?=\n## [^#]|\Z)", "", target_text, flags=re.DOTALL)
    target_text = re.sub(r"\n## Alt Text\n\n?.*?(?=\n## [^#]|\Z)", "", target_text, flags=re.DOTALL)

    output_file.write_text(target_text)

    # Store selected slides in frontmatter if provided (for scheduling later)
    if selected_slides:
        text = output_file.read_text()
        fm_end = text.index("\n---", 4)
        text = text[:fm_end] + f'\ntwitter_slides: "{selected_slides}"' + text[fm_end:]
        output_file.write_text(text)

    # Generate caption in background
    job_id = str(uuid.uuid4())[:8]
    with job_lock:
        jobs[job_id] = {"status": "generating", "caption_status": "generating"}

    thread = threading.Thread(
        target=_run_caption_generation,
        args=(job_id, target_platform, category, topic, icp, output_file),
    )
    thread.start()

    rel_path = str(output_file.relative_to(OUTPUT_DIR))
    return jsonify({"success": True, "path": rel_path, "job_id": job_id})


# ── Serve generated slide images ─────────────────────────────────────

@app.route("/slides/<path:filepath>")
def serve_slide(filepath):
    return send_from_directory(str(SLIDES_DIR), filepath)


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    _p = argparse.ArgumentParser()
    _p.add_argument("--port", type=int, default=5000)
    _args = _p.parse_args()
    app.run(debug=True, host="127.0.0.1", port=_args.port)
