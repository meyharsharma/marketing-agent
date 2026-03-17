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

# ── Post-render self-check configuration ──────────────────────────────
# Maps slide types to their text selectors, default font sizes, and
# minimum font sizes for the post-render check/fix pass.
# The existing in-HTML auto-scale scripts run first (on page load);
# this check catches cases where text *still* overflows at those minimums.

SLIDE_CHECK_CONFIG = {
    "hook": {
        "elements": [
            {
                "selector": ".hook-title",
                "role": "hook",
                "default_size": 118,
                "min_size": 38,
                "step": 4,
            },
        ],
        "container": ".notebook__content",
        "notebook": ".notebook__body",
        "max_notebook_grow": 60,
    },
    "old_way": {
        "elements": [
            {
                "selector": ".body-text",
                "role": "body",
                "default_size": 34,
                "min_size": 17,
                "step": 1,
            },
        ],
        "container": ".notebook__content",
        "notebook": ".notebook__body",
        "max_notebook_grow": 60,
    },
    "the_switch": {
        "elements": [
            {
                "selector": ".body-text",
                "role": "body",
                "default_size": 34,
                "min_size": 17,
                "step": 1,
            },
        ],
        "container": ".notebook__content",
        "notebook": ".notebook__body",
        "max_notebook_grow": 60,
    },
    "result": {
        "elements": [
            {
                "selector": ".body-text",
                "role": "body",
                "default_size": 34,
                "min_size": 17,
                "step": 1,
            },
            {
                "selector": ".quote-text",
                "role": "quote",
                "default_size": 24,
                "min_size": 14,
                "step": 1,
            },
        ],
        "container": ".notebook__content",
        "notebook": ".notebook__body",
        "max_notebook_grow": 60,
    },
    "payoff": {
        "elements": [
            {
                "selector": ".body-text",
                "role": "body",
                "default_size": 34,
                "min_size": 17,
                "step": 1,
            },
        ],
        "container": ".notebook__content",
        "notebook": ".notebook__body",
        "max_notebook_grow": 60,
    },
    "cta": {
        "elements": [
            {
                "selector": ".cta-headline",
                "role": "cta-headline",
                "default_size": 64,
                "min_size": 36,
                "step": 4,
            },
            {
                "selector": ".cta-url",
                "role": "cta-url",
                "default_size": 34,
                "min_size": 22,
                "step": 2,
            },
            {
                "selector": ".cta-sub",
                "role": "cta-sub",
                "default_size": 40,
                "min_size": 24,
                "step": 2,
            },
        ],
        "container": ".notebook__content",
        "notebook": ".notebook__body",
        "max_notebook_grow": 60,
    },
}

# JavaScript injected via page.evaluate() to diagnose text issues.
# Runs AFTER the in-HTML auto-scale scripts have already executed.
# Returns a list of issue dicts for each text element.
CHECK_JS = """
(config) => {
    const issues = [];
    const container = document.querySelector(config.container);
    if (!container) return issues;

    const containerRect = container.getBoundingClientRect();

    for (const elCfg of config.elements) {
        const el = document.querySelector(elCfg.selector);
        if (!el) continue;

        const computed = window.getComputedStyle(el);
        const fontSize = parseFloat(computed.fontSize);
        const elRect = el.getBoundingClientRect();

        // Check 1: element content overflows its own box
        const overflows = el.scrollHeight > el.clientHeight + 2;

        // Check 2: element extends beyond the notebook content container
        const exceedsBounds = elRect.bottom > containerRect.bottom + 2
                           || elRect.right > containerRect.right + 2;

        // Check 3: font size fell below readable threshold
        const tooSmall = fontSize < elCfg.min_size;

        if (overflows || exceedsBounds || tooSmall) {
            issues.push({
                selector: elCfg.selector,
                role: elCfg.role,
                fontSize: fontSize,
                minSize: elCfg.min_size,
                step: elCfg.step,
                overflows: overflows,
                exceedsBounds: exceedsBounds,
                tooSmall: tooSmall,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight,
                textLength: el.textContent.length,
            });
        }
    }

    // Also check the container itself for overflow
    if (container.scrollHeight > container.clientHeight + 2) {
        issues.push({
            selector: config.container,
            role: 'container',
            overflows: true,
            exceedsBounds: false,
            tooSmall: false,
            scrollHeight: container.scrollHeight,
            clientHeight: container.clientHeight,
            textLength: 0,
        });
    }

    return issues;
}
"""

# JavaScript injected to attempt auto-fixes in the live DOM.
# Only adjusts font size and notebook height — never changes font family,
# colors, or layout structure.
# Returns a list of actions taken or failure reports.
FIX_JS = """
(config) => {
    const results = [];
    const container = document.querySelector(config.container);
    const notebook = document.querySelector(config.notebook);
    if (!container) return results;

    let notebookGrown = 0;
    const maxGrow = config.max_notebook_grow || 60;

    for (const elCfg of config.elements) {
        const el = document.querySelector(elCfg.selector);
        if (!el) continue;

        const origSize = parseFloat(window.getComputedStyle(el).fontSize);
        let size = origSize;
        let fixed = false;

        // Step 1: Reduce font size down to min
        while ((el.scrollHeight > container.clientHeight + 2) && size > elCfg.min_size) {
            size -= elCfg.step;
            el.style.fontSize = size + 'px';
        }

        // Check if that resolved it
        if (el.scrollHeight <= container.clientHeight + 2) {
            if (size < origSize) {
                results.push({
                    selector: elCfg.selector,
                    role: elCfg.role,
                    action: 'reduced_font',
                    from: origSize,
                    to: size,
                    status: 'fixed',
                });
            }
            continue;
        }

        // Step 2: Grow notebook height slightly
        if (notebook && notebookGrown < maxGrow) {
            const grow = Math.min(maxGrow - notebookGrown, 60);
            const currentH = notebook.getBoundingClientRect().height;
            notebook.style.height = (currentH + grow) + 'px';

            // Also grow the shadow to match
            const shadow = notebook.querySelector('.notebook__shadow');
            if (shadow) {
                shadow.style.height = '100%';
            }

            // Grow the SVG viewBox if present
            const svg = notebook.querySelector('svg');
            if (svg) {
                const vb = svg.getAttribute('viewBox');
                if (vb) {
                    const parts = vb.split(' ');
                    parts[3] = String(parseFloat(parts[3]) + grow);
                    svg.setAttribute('viewBox', parts.join(' '));
                }
                const rect = svg.querySelector('rect');
                if (rect) {
                    rect.setAttribute('height',
                        String(parseFloat(rect.getAttribute('height')) + grow));
                }
            }

            notebookGrown += grow;

            // Check if growing fixed it
            if (el.scrollHeight <= container.clientHeight + 2) {
                results.push({
                    selector: elCfg.selector,
                    role: elCfg.role,
                    action: 'reduced_font_and_grew_notebook',
                    fontFrom: origSize,
                    fontTo: size,
                    notebookGrew: grow,
                    status: 'fixed',
                });
                continue;
            }
        }

        // Step 3: Still overflowing — report unfixable
        const excess = el.scrollHeight - container.clientHeight;
        // Rough estimate: chars to trim ≈ excess / lineHeight * charsPerLine
        const lineH = parseFloat(window.getComputedStyle(el).lineHeight) || size * 1.4;
        const charW = size * 0.6;
        const containerW = container.clientWidth;
        const charsPerLine = Math.floor(containerW / charW);
        const excessLines = Math.ceil(excess / lineH);
        const trimChars = Math.max(10, excessLines * charsPerLine);

        results.push({
            selector: elCfg.selector,
            role: elCfg.role,
            action: 'none',
            fontFrom: origSize,
            fontTo: size,
            status: 'fail',
            trimChars: trimChars,
        });
    }

    return results;
}
"""


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


def check_slide(page, slide_type: str) -> list:
    """Inject JS to diagnose text overflow/readability issues on the current page."""
    config = SLIDE_CHECK_CONFIG.get(slide_type)
    if not config:
        return []
    return page.evaluate(CHECK_JS, config) or []


def fix_slide(page, slide_type: str) -> list:
    """Inject JS to auto-fix text issues in the live DOM before screenshotting."""
    config = SLIDE_CHECK_CONFIG.get(slide_type)
    if not config:
        return []
    return page.evaluate(FIX_JS, config) or []


def print_slide_report(report: list):
    """Print a summary of the post-render check results."""
    if not report:
        return
    print("\n  ── Post-render check ──")
    has_failures = False
    for entry in report:
        slide_num = entry["slide_num"]
        slide_type = entry["slide_type"]
        status = entry["status"]

        if status == "pass":
            print(f"  Slide {slide_num} ({slide_type}): PASS")
        elif status == "fixed":
            fixes = entry.get("fixes", [])
            fix_desc = "; ".join(
                f"{f['role']} reduced from {f.get('from', f.get('fontFrom', '?'))}px"
                f" to {f.get('to', f.get('fontTo', '?'))}px"
                for f in fixes
            )
            print(f"  Slide {slide_num} ({slide_type}): FIXED - {fix_desc}")
        elif status == "fail":
            has_failures = True
            fails = entry.get("fails", [])
            fail_desc = "; ".join(
                f"{f['role']} still overflows (trim ~{f.get('trimChars', '?')} chars)"
                for f in fails
            )
            print(f"  Slide {slide_num} ({slide_type}): FAIL - {fail_desc}")

    if has_failures:
        print("  ⚠ Some slides need content trimming — see FAIL entries above.")
    print()


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

    # Use template dimensions if specified, otherwise fall back to defaults
    dims = template.get("dimensions", {})
    width = dims.get("width", SLIDE_WIDTH)
    height = dims.get("height", SLIDE_HEIGHT)

    # Collect check results for the summary report
    check_report = []

    # Render with Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})

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

            # ── Post-render self-check ──
            # The in-HTML auto-scale scripts have already run.
            # Now check if text still overflows or is unreadable.
            issues = check_slide(page, slide_type)

            if issues:
                # Attempt auto-fix in the live DOM
                fix_results = fix_slide(page, slide_type)

                fixed = [r for r in fix_results if r.get("status") == "fixed"]
                failed = [r for r in fix_results if r.get("status") == "fail"]

                if failed:
                    check_report.append({
                        "slide_num": i + 1,
                        "slide_type": slide_type,
                        "status": "fail",
                        "fails": failed,
                        "fixes": fixed,
                    })
                elif fixed:
                    check_report.append({
                        "slide_num": i + 1,
                        "slide_type": slide_type,
                        "status": "fixed",
                        "fixes": fixed,
                    })
                else:
                    check_report.append({
                        "slide_num": i + 1,
                        "slide_type": slide_type,
                        "status": "pass",
                    })
            else:
                check_report.append({
                    "slide_num": i + 1,
                    "slide_type": slide_type,
                    "status": "pass",
                })

            # Screenshot (captures the fixed DOM if fixes were applied)
            filename = f"slide_{i + 1:02d}_{slide_type}.png"
            filepath = out_dir / filename
            page.screenshot(path=str(filepath))
            print(f"  Created: {filepath.relative_to(PROJECT_ROOT)}")

            # Clean up temp file
            tmp_file.unlink()

        browser.close()

    print(f"\nRendered {len(slide_list)} slides to: {out_dir.relative_to(PROJECT_ROOT)}/")
    print_slide_report(check_report)
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
