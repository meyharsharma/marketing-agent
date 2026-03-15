"""
Template-driven carousel renderer.

Reads a template definition (YAML) + content (YAML) and renders
each slide to PNG using Playwright (HTML/CSS → screenshot).

Usage:
    python scripts/render_carousel.py templates/autopsy.yaml content.yaml

    # Or render from a post markdown file (auto-extracts content):
    python scripts/render_carousel.py templates/autopsy.yaml output/instagram/autopsy/2026-03-14_fix-my-code.md

Output: generated_slides/{slug}/ with one PNG per slide.
"""

import re
import sys
import yaml
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "generated_slides"

SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1080


def load_template(template_path: Path) -> dict:
    """Load the template YAML definition."""
    with open(template_path) as f:
        return yaml.safe_load(f)


def load_content(content_path: Path) -> dict:
    """Load content from YAML or extract from markdown."""
    text = content_path.read_text()

    if content_path.suffix == ".md":
        return extract_content_from_markdown(text)

    return yaml.safe_load(text)


def extract_content_from_markdown(md_text: str) -> dict:
    """Extract slide content from the standard markdown output format."""
    content = {"slides": []}

    # Find ## Slides section
    slides_match = re.search(
        r'^## Slides\s*\n(.*?)(?=^## [^#]|\Z)', md_text,
        re.MULTILINE | re.DOTALL
    )
    if not slides_match:
        return content

    slides_section = slides_match.group(1)

    # Parse ### Slide N — Title blocks
    slide_pattern = r'^### Slide \d+\s*[-\u2013\u2014]\s*(.+?)\n(.*?)(?=^### Slide|\Z)'
    for m in re.finditer(slide_pattern, slides_section, re.MULTILINE | re.DOTALL):
        title = m.group(1).strip()
        body = m.group(2).strip()
        content["slides"].append({"title": title, "content": body})

    return content


def fill_template(html: str, placeholders: dict) -> str:
    """Replace {{placeholder}} markers in HTML with content values."""
    for key, value in placeholders.items():
        # Escape HTML entities in content
        safe_value = (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        html = html.replace(f"{{{{{key}}}}}", safe_value)

    # Remove any unfilled placeholders
    html = re.sub(r'\{\{[^}]+\}\}', '', html)
    return html


def resolve_slide_list(template: dict, content: dict) -> list:
    """
    Build the ordered list of slides to render, expanding repeatable types.

    Returns list of dicts: [{type, html_file, placeholders}, ...]
    """
    template_dir = None  # set by caller
    slides = []
    content_slides = content.get("slides", [])

    # If content is in the indexed format (slides list), use positional mapping
    if content_slides and isinstance(content_slides[0], dict) and "title" in content_slides[0]:
        return _resolve_from_markdown_slides(template, content_slides)

    # Otherwise, content uses named placeholders per slide type
    for slide_def in template["slides"]:
        slide_type = slide_def["type"]

        if slide_def.get("repeat"):
            # Find all numbered entries: dissection_1, dissection_2, etc.
            i = 1
            while True:
                key = f"{slide_type}_{i}"
                if key in content:
                    placeholders = dict(content[key])
                    # Auto-cycle variant if not explicitly set
                    if "variant" not in placeholders:
                        placeholders["variant"] = str(((i - 1) % 3) + 1)
                    slides.append({
                        "type": slide_type,
                        "placeholders": placeholders,
                    })
                    i += 1
                else:
                    break

            # Also check for unnumbered list format
            if i == 1 and slide_type in content and isinstance(content[slide_type], list):
                for idx, item in enumerate(content[slide_type]):
                    placeholders = dict(item)
                    if "variant" not in placeholders:
                        placeholders["variant"] = str((idx % 3) + 1)
                    slides.append({
                        "type": slide_type,
                        "placeholders": placeholders,
                    })
        else:
            placeholders = content.get(slide_type, {})
            slides.append({
                "type": slide_type,
                "placeholders": placeholders,
            })

    return slides


def _resolve_from_markdown_slides(template: dict, md_slides: list) -> list:
    """Map markdown slides to template types using title-based classification."""
    slides = []
    total = len(md_slides)

    for i, ms in enumerate(md_slides):
        title = ms.get("title", "").lower()
        content = ms.get("content", "")

        if i == 0 or "hook" in title:
            # Parse hook: split into prompt_text and hook_line
            lines = content.strip().split("\n")
            prompt_lines = []
            hook_line = ""
            found_break = False
            for line in lines:
                stripped = line.strip()
                if not stripped and prompt_lines:
                    found_break = True
                    continue
                if found_break:
                    hook_line = stripped
                else:
                    prompt_lines.append(stripped)
            if not hook_line and len(prompt_lines) > 1:
                hook_line = prompt_lines.pop()

            slides.append({
                "type": "hook",
                "placeholders": {
                    "prompt_text": " ".join(prompt_lines).strip('"').strip("'"),
                    "hook_line": hook_line,
                },
            })
        elif "model" in title and "hear" in title:
            # Strip markdown formatting
            body = re.sub(r'\*\*[^*]+\*\*\s*', '', content).strip()
            body = re.sub(r'^[^:]+:\s*', '', body, count=1).strip().strip('"')
            slides.append({
                "type": "model_hears",
                "placeholders": {"content": body},
            })
        elif "optimiz" in title or "optimis" in title:
            # Strip model label
            raw_lines = content.strip().split("\n")
            prompt_lines = [
                l for l in raw_lines
                if not re.match(r'(?i)(optimized for|optimised for|model:)', l.strip())
            ]
            slides.append({
                "type": "optimized",
                "placeholders": {"prompt": "\n".join(prompt_lines).strip()},
            })
        elif i == total - 1 or "payoff" in title or "closing" in title:
            lines = [
                l.strip() for l in content.strip().split("\n")
                if l.strip() and not re.match(r'(?i)(prompt optimizer|@|branding)', l.strip())
            ]
            heading = lines[0] if lines else "THE TAKEAWAY"
            body = " ".join(lines[1:]) if len(lines) > 1 else ""
            slides.append({
                "type": "payoff",
                "placeholders": {"heading": heading, "body": body},
            })
        else:
            # Dissection slide
            lines = content.strip().split("\n")
            heading = ms.get("title", "ISSUE")
            body = " ".join(
                l.strip().strip("*").strip("#").strip()
                for l in lines if l.strip()
            )
            slides.append({
                "type": "dissection",
                "placeholders": {"title": heading, "body": body},
            })

    return slides


def render_slides(template_path: str, content_path: str, output_slug: str = None):
    """Main entry: render all slides from template + content."""
    template_path = Path(template_path)
    content_path = Path(content_path)

    template = load_template(template_path)
    content = load_content(content_path)

    # Determine template HTML directory
    template_dir = template_path.parent / template_path.stem
    if not template_dir.is_dir():
        print(f"Error: Template HTML directory not found: {template_dir}")
        sys.exit(1)

    # Build slide list
    slide_list = resolve_slide_list(template, content)
    if not slide_list:
        print("Error: No slides to render. Check your content file.")
        sys.exit(1)

    # Output directory
    slug = output_slug or content_path.stem
    out_dir = OUTPUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Render with Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT})

        for i, slide in enumerate(slide_list):
            slide_type = slide["type"]
            html_file = template_dir / f"{slide_type}.html"

            if not html_file.exists():
                print(f"  Warning: No HTML template for type '{slide_type}', skipping")
                continue

            html = html_file.read_text()
            html = fill_template(html, slide["placeholders"])

            # Navigate to the HTML (file:// URL so relative paths work)
            # Write filled HTML to a temp file in the template dir
            tmp_file = template_dir / f"_render_{i}.html"
            tmp_file.write_text(html)

            page.goto(f"file://{tmp_file.resolve()}")
            page.wait_for_load_state("networkidle")

            # Screenshot
            filename = f"slide_{i + 1:02d}_{slide_type}.png"
            filepath = out_dir / filename
            page.screenshot(path=str(filepath))
            print(f"  Created: {filepath.relative_to(PROJECT_ROOT)}")

            # Clean up temp file
            tmp_file.unlink()

        browser.close()

    print(f"\nRendered {len(slide_list)} slides to: {out_dir.relative_to(PROJECT_ROOT)}/")
    return out_dir


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/render_carousel.py <template.yaml> <content.yaml>")
        print("       python scripts/render_carousel.py <template.yaml> <post.md>")
        sys.exit(1)

    template_arg = sys.argv[1]
    content_arg = sys.argv[2]
    slug_arg = sys.argv[3] if len(sys.argv) > 3 else None

    render_slides(template_arg, content_arg, slug_arg)
