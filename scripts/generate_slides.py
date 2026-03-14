"""
Generate Instagram carousel slide images from a post markdown file.

Usage:
    python scripts/generate_slides.py output/instagram/autopsy/2026-03-11_fix-my-code.md

Images are saved to: generated_slides/{slug}/ in the project root.
"""

import re
import sys
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --- Config ---
WIDTH = 1080
HEIGHT = 1080

# Colors matching the Canva template exactly
CORAL = "#E93B04"
BLACK = "#000000"
CREAM = "#FFF8F1"
WHITE = "#FFFFFF"

# Sidebar
SIDEBAR_WIDTH = 50
SIDEBAR_X = WIDTH - SIDEBAR_WIDTH  # starts at 1030

# Handle text
HANDLE = "@PROMPTOPTIMIZR"

# Padding
PAD_LEFT = 60
PAD_TOP = 60
PAD_RIGHT = SIDEBAR_X - 40  # content must not overlap sidebar
CONTENT_WIDTH = PAD_RIGHT - PAD_LEFT

# Arrow circle dimensions - smaller size
ARROW_RADIUS = 55
ARROW_CX = 920
ARROW_CY_CENTER = HEIGHT // 2       # for hook slide (vertically centered)
ARROW_CY_BOTTOM = HEIGHT - 60 - 55  # for all other slides (bottom-right)

# Bookmark icon dimensions (for optimized slide)
BOOKMARK_SIZE = 100
BOOKMARK_X = 910
BOOKMARK_Y = HEIGHT // 2 - 50

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "generated_slides"

# Font path - Open Sans Condensed ExtraBold (matches Canva template)
FONT_PRIMARY = PROJECT_ROOT / "fonts" / "OpenSans-CondensedExtraBold.ttf"
FONT_FALLBACK = PROJECT_ROOT / "fonts" / "OpenSans-CondensedBold.ttf"


def load_font(size=48):
    """Load Open Sans Condensed ExtraBold."""
    if Path(FONT_PRIMARY).exists():
        return ImageFont.truetype(str(FONT_PRIMARY), size)
    if Path(FONT_FALLBACK).exists():
        return ImageFont.truetype(str(FONT_FALLBACK), size)
    return ImageFont.load_default(size=size)


def wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def wrap_text_preserve_newlines(text, font, max_width, draw):
    """Wrap text while preserving original line breaks from the source."""
    all_lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            all_lines.append("")
            continue
        wrapped = wrap_text(paragraph, font, max_width, draw)
        all_lines.extend(wrapped)
    return all_lines


def get_text_height(lines, font, draw, line_spacing=1.3):
    """Calculate total height for wrapped text lines."""
    if not lines:
        return 0
    total = 0
    for line in lines:
        if line == "":
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            total += (bbox[3] - bbox[1]) * 0.6
        else:
            bbox = draw.textbbox((0, 0), line, font=font)
            total += (bbox[3] - bbox[1]) * line_spacing
    return int(total)


def draw_left_text(draw, lines, x, y, font, fill, line_spacing=1.3):
    """Draw lines of text left-aligned at x position. Returns y after last line."""
    current_y = y
    for line in lines:
        if line == "":
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            current_y += int((bbox[3] - bbox[1]) * 0.6)
            continue
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        draw.text((x, current_y), line, font=font, fill=fill)
        current_y += int(line_height * line_spacing)
    return current_y


def draw_justified_text(draw, lines, x, y, font, fill, max_width, line_spacing=1.3):
    """Draw lines of text justified (spaced to fill max_width). Last line left-aligned."""
    current_y = y
    for idx, line in enumerate(lines):
        if line == "":
            bbox = draw.textbbox((0, 0), "Ay", font=font)
            current_y += int((bbox[3] - bbox[1]) * 0.6)
            continue
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        words = line.split()
        # Last line or single word: left-align
        if idx == len(lines) - 1 or len(words) <= 1:
            draw.text((x, current_y), line, font=font, fill=fill)
        else:
            # Calculate total word width
            total_word_width = sum(
                draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0]
                for w in words
            )
            total_space = max_width - total_word_width
            gap = total_space / (len(words) - 1) if len(words) > 1 else 0
            cx = x
            for w in words:
                draw.text((cx, current_y), w, font=font, fill=fill)
                ww = draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0]
                cx += ww + gap
        current_y += int(line_height * line_spacing)
    return current_y


def strip_emdashes(text):
    """Remove all em dashes and en dashes, replace with regular dash."""
    text = text.replace("\u2014", " - ")
    text = text.replace("\u2013", " - ")
    return text


def draw_sidebar(draw, color):
    """Draw the right sidebar stripe."""
    draw.rectangle([SIDEBAR_X, 0, WIDTH, HEIGHT], fill=color)


def draw_handle(draw, x, y, color=BLACK, size=20):
    """Draw the @PROMPTOPTIMIZR handle."""
    font = load_font(size)
    draw.text((x, y), HANDLE, font=font, fill=color)


# Arrow icon paths
ARROW1_PATH = PROJECT_ROOT / "arrow1.png"  # cream/white circle, coral arrow (hook slide)
ARROW2_PATH = PROJECT_ROOT / "arrow2.png"  # coral circle, black arrow (other slides)

# Arrow icon display size
ARROW_ICON_SIZE = 160


def paste_arrow(img, arrow_type="arrow1", cx=None, cy=None, size=None):
    """Paste an arrow icon onto the image, centered at (cx, cy)."""
    cx = cx or ARROW_CX
    cy = cy or ARROW_CY_BOTTOM
    size = size or ARROW_ICON_SIZE

    icon_path = ARROW1_PATH if arrow_type == "arrow1" else ARROW2_PATH
    if not icon_path.exists():
        return

    icon = Image.open(icon_path).convert("RGBA")
    icon = icon.resize((size, size), Image.LANCZOS)

    # Calculate top-left position from center
    x = int(cx - size // 2)
    y = int(cy - size // 2)

    # Paste with alpha mask
    img.paste(icon, (x, y), icon)


def draw_bookmark_icon(draw, x, y, size, bg_color, icon_color):
    """Draw a rounded rectangle with bookmark shape inside."""
    # Rounded rect background
    r = 15
    x1, y1, x2, y2 = x, y, x + size, y + size
    draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=bg_color)

    # Bookmark shape inside
    bx = x + size // 4
    by = y + size // 5
    bw = size // 2
    bh = int(size * 0.6)
    # Rectangle part
    draw.rectangle([bx, by, bx + bw, by + bh], fill=icon_color)
    # Bottom notch (triangle cut)
    mid = bx + bw // 2
    bottom = by + bh
    notch = bh // 4
    draw.polygon([
        (bx, bottom),
        (mid, bottom - notch),
        (bx + bw, bottom),
        (bx + bw, bottom + 2),
        (bx, bottom + 2),
    ], fill=bg_color)


# ---- SLIDE TYPES ----

def _draw_hook_slide(draw, content, img):
    """Slide 1: Coral background, 'BAD PROMPT' black top-left, hook line white, arrow mid-right, cream sidebar."""
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

    prompt_text = " ".join(prompt_lines).strip('"').strip("'")

    # Background: coral
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=CORAL)
    # Cream sidebar on right
    draw_sidebar(draw, CREAM)

    # Text must not cross arrow area - arrow is at ARROW_CX, limit text width
    arrow_left_edge = ARROW_CX - ARROW_ICON_SIZE // 2 - 20  # 20px gap before arrow
    hook_text_width = arrow_left_edge - PAD_LEFT

    # Auto-scale: start at 120, reduce until text fits vertically
    max_height = HEIGHT - 120  # leave 60px top/bottom margin
    gap = 30
    font_size = 120
    while font_size >= 48:
        prompt_font = load_font(size=font_size)
        hook_font = load_font(size=min(font_size, 100))
        prompt_upper = f'"{prompt_text.upper()}"'
        prompt_wrapped = wrap_text(prompt_upper, prompt_font, hook_text_width, draw)
        prompt_h = get_text_height(prompt_wrapped, prompt_font, draw, line_spacing=1.15)
        hook_wrapped = wrap_text(hook_line.upper(), hook_font, hook_text_width, draw) if hook_line else []
        hook_h = get_text_height(hook_wrapped, hook_font, draw, line_spacing=1.15) if hook_wrapped else 0
        total_h = prompt_h + gap + hook_h
        if total_h <= max_height:
            break
        font_size -= 4

    # Position: center the whole block, then shift only the bad prompt up
    start_y = (HEIGHT - total_h) // 2
    hook_y = start_y + prompt_h + gap  # hook line stays at its centered position

    # Draw bad prompt shifted up
    draw_left_text(draw, prompt_wrapped, PAD_LEFT, start_y - 40, prompt_font, BLACK, line_spacing=1.15)
    # Draw hook line at original position
    if hook_wrapped:
        draw_left_text(draw, hook_wrapped, PAD_LEFT, hook_y, hook_font, WHITE, line_spacing=1.15)

    # Arrow icon - centered vertically on the slide, right side
    paste_arrow(img, "arrow1", cx=ARROW_CX, cy=HEIGHT // 2)

    # Handle bottom-right
    draw_handle(draw, SIDEBAR_X - 260, HEIGHT - 60, BLACK, 20)


def _draw_model_hears_slide(draw, content):
    """Slide 2: Cream bg, coral heading, black body, coral sidebar."""
    # Background: cream
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=CREAM)
    draw_sidebar(draw, CORAL)

    # Handle top-right
    draw_handle(draw, SIDEBAR_X - 260, PAD_TOP, BLACK, 20)

    # "WHAT IT HEARD" heading
    header_font = load_font(size=96)
    y = PAD_TOP + 60
    header_wrapped = wrap_text("WHAT IT HEARD", header_font, CONTENT_WIDTH, draw)
    y = draw_left_text(draw, header_wrapped, PAD_LEFT, y, header_font, CORAL, line_spacing=1.0)

    # Body content
    y += 180
    body_font = load_font(size=44)

    # Parse content - strip markdown
    body_text = re.sub(r'\*\*[^*]+\*\*\s*', '', content).strip()
    body_text = re.sub(r'^[^:]+:\s*', '', body_text, count=1).strip().strip('"')
    body_wrapped = wrap_text(body_text, body_font, CONTENT_WIDTH - 40, draw)
    draw_justified_text(draw, body_wrapped, PAD_LEFT, y, body_font, BLACK, CONTENT_WIDTH - 40, line_spacing=1.5)


def _draw_dissection_slide(draw, content, title=""):
    """Dissection slides: Black bg, coral heading, white body, coral sidebar."""
    # Background: black
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=BLACK)
    draw_sidebar(draw, CORAL)

    # Handle top-right
    draw_handle(draw, SIDEBAR_X - 260, PAD_TOP, WHITE, 20)

    # Heading
    if title:
        failure_name = title.upper()
    else:
        lines = content.strip().split("\n")
        failure_name = lines[0].strip().strip("*#").strip().upper() if lines else "ISSUE"

    header_font = load_font(size=96)
    y = PAD_TOP + 60
    header_wrapped = wrap_text(failure_name, header_font, CONTENT_WIDTH, draw)
    y = draw_left_text(draw, header_wrapped, PAD_LEFT, y, header_font, CORAL, line_spacing=1.0)

    # Body content
    y += 180
    body_font = load_font(size=44)
    body_text = " ".join(
        line.strip().strip("*").strip("#").strip()
        for line in content.strip().split("\n")
        if line.strip()
    )
    body_wrapped = wrap_text(body_text, body_font, CONTENT_WIDTH - 40, draw)
    draw_justified_text(draw, body_wrapped, PAD_LEFT, y, body_font, WHITE, CONTENT_WIDTH - 40, line_spacing=1.5)


def _draw_optimized_slide(draw, content):
    """Optimized slide: Coral bg, 'OPTIMIZED PROMPT' white, prompt in black, bookmark icon."""
    # Background: coral
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=CORAL)

    # "OPTIMIZED PROMPT" large white heading
    header_font = load_font(size=96)
    y = PAD_TOP
    header_wrapped = wrap_text("OPTIMIZED PROMPT", header_font, CONTENT_WIDTH, draw)
    y = draw_left_text(draw, header_wrapped, PAD_LEFT, y, header_font, WHITE, line_spacing=1.0)

    # The actual optimized prompt text in black
    y += 120
    body_font = load_font(size=38)

    # Strip model label line
    raw_lines = content.strip().split("\n")
    prompt_lines = []
    for line in raw_lines:
        stripped = line.strip()
        if re.match(r'(?i)(optimized for|optimised for|model:)', stripped):
            continue
        prompt_lines.append(line)

    prompt_text = "\n".join(prompt_lines).strip()
    body_max_width = BOOKMARK_X - PAD_LEFT - 30
    indent = 40  # indentation for bullet lines starting with -

    # Draw lines with indentation for bullet points
    current_y = y
    for paragraph in prompt_text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            bbox = draw.textbbox((0, 0), "Ay", font=body_font)
            current_y += int((bbox[3] - bbox[1]) * 0.6)
            continue
        is_bullet = paragraph.startswith("-")
        x_offset = PAD_LEFT + indent if is_bullet else PAD_LEFT
        wrap_width = body_max_width - indent if is_bullet else body_max_width
        wrapped = wrap_text(paragraph, body_font, wrap_width, draw)
        current_y = draw_left_text(draw, wrapped, x_offset, current_y, body_font, BLACK, line_spacing=1.5)

    # Bookmark icon
    draw_bookmark_icon(draw, BOOKMARK_X, BOOKMARK_Y, BOOKMARK_SIZE, CREAM, BLACK)

    # Handle bottom-right
    draw_handle(draw, SIDEBAR_X - 260, HEIGHT - 60, BLACK, 20)


def _draw_payoff_slide(draw, content):
    """Final slide: Cream bg, coral heading, black body text, coral sidebar."""
    # Background: cream
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=CREAM)
    draw_sidebar(draw, CORAL)

    # Parse content
    lines = content.strip().split("\n")
    payoff_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not re.match(r'(?i)(prompt optimizer|@|branding)', stripped):
            payoff_lines.append(stripped)

    # Split into heading (first line) and body (rest)
    heading_text = payoff_lines[0].upper() if payoff_lines else "THE TAKEAWAY"
    body_text = " ".join(payoff_lines[1:]) if len(payoff_lines) > 1 else ""

    # Heading
    header_font = load_font(size=96)
    y = PAD_TOP + 60
    header_wrapped = wrap_text(heading_text, header_font, CONTENT_WIDTH, draw)
    y = draw_left_text(draw, header_wrapped, PAD_LEFT, y, header_font, CORAL, line_spacing=1.0)

    # Body / CTA
    y += 80
    if body_text:
        body_font = load_font(size=44)
        body_wrapped = wrap_text(body_text, body_font, CONTENT_WIDTH - 40, draw)
        draw_justified_text(draw, body_wrapped, PAD_LEFT, y, body_font, BLACK, CONTENT_WIDTH - 40, line_spacing=1.5)
    else:
        # Default CTA
        cta_font = load_font(size=44)
        cta_text = "Try Prompt Optimizer - link in bio"
        cta_wrapped = wrap_text(cta_text, cta_font, CONTENT_WIDTH, draw)
        draw_left_text(draw, cta_wrapped, PAD_LEFT, y, cta_font, BLACK, line_spacing=1.5)

    # Handle bottom-right
    draw_handle(draw, SIDEBAR_X - 260, HEIGHT - 60, BLACK, 20)


def _draw_generic_slide(draw, content):
    """Fallback: black bg, white text, coral sidebar."""
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=BLACK)
    draw_sidebar(draw, CORAL)

    body_font = load_font(size=34)
    wrapped = wrap_text(content.strip(), body_font, CONTENT_WIDTH, draw)
    y = PAD_TOP + 60
    draw_left_text(draw, wrapped, PAD_LEFT, y, body_font, WHITE)

    draw_handle(draw, SIDEBAR_X - 260, PAD_TOP, WHITE, 20)


# ---- MAIN LOGIC ----

def create_slide(slide_type, content, title=""):
    """Create a single slide image. Returns a PIL Image."""
    content = strip_emdashes(content)
    title = strip_emdashes(title)

    img = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)

    if slide_type == "hook":
        _draw_hook_slide(draw, content, img)
    elif slide_type == "model_hears":
        _draw_model_hears_slide(draw, content)
        paste_arrow(img, "arrow2", cx=ARROW_CX, cy=ARROW_CY_BOTTOM)
    elif slide_type == "dissection":
        _draw_dissection_slide(draw, content, title=title)
        paste_arrow(img, "arrow2", cx=ARROW_CX, cy=ARROW_CY_BOTTOM)
    elif slide_type == "optimized":
        _draw_optimized_slide(draw, content)
    elif slide_type == "payoff":
        _draw_payoff_slide(draw, content)
    else:
        _draw_generic_slide(draw, content)
        paste_arrow(img, "arrow2", cx=ARROW_CX, cy=ARROW_CY_BOTTOM)

    return img


def classify_slide(title, index, total):
    """Determine slide type from its title and position."""
    title_lower = title.lower()
    if index == 0 or "hook" in title_lower:
        return "hook"
    if "model" in title_lower and ("hear" in title_lower or "hears" in title_lower):
        return "model_hears"
    if "what" in title_lower and "hear" in title_lower:
        return "model_hears"
    if "optimiz" in title_lower or "optimis" in title_lower:
        return "optimized"
    if index == total - 1 or "payoff" in title_lower or "closing" in title_lower:
        return "payoff"
    return "dissection"


def parse_slides_from_markdown(md_text):
    """Extract slides from the output markdown format."""
    slides = []

    slides_match = re.search(r'^## Slides\s*\n(.*?)(?=^## [^#]|\Z)', md_text, re.MULTILINE | re.DOTALL)
    if not slides_match:
        slide_pattern = r'^### Slide \d+\s*[^\n]*\n(.*?)(?=^### Slide|\Z)'
        for m in re.finditer(slide_pattern, md_text, re.MULTILINE | re.DOTALL):
            title_match = re.match(r'^### Slide \d+\s*[-\u2013\u2014]\s*(.+)', m.group(0).split("\n")[0])
            title = title_match.group(1).strip() if title_match else ""
            content = "\n".join(m.group(0).split("\n")[1:]).strip()
            slides.append({"title": title, "content": content})
        return slides

    slides_section = slides_match.group(1)
    slide_pattern = r'^### Slide \d+\s*[-\u2013\u2014]\s*(.+?)\n(.*?)(?=^### Slide|\Z)'
    for m in re.finditer(slide_pattern, slides_section, re.MULTILINE | re.DOTALL):
        slides.append({"title": m.group(1).strip(), "content": m.group(2).strip()})

    return slides


def generate_slides(markdown_path):
    """Main function: parse markdown, generate images, save to folder."""
    md_path = Path(markdown_path)
    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)

    md_text = md_path.read_text()
    slides = parse_slides_from_markdown(md_text)

    if not slides:
        print("Error: No slides found in the markdown file.")
        print("Expected format: ### Slide 1 - Title\\ncontent...")
        sys.exit(1)

    slug = md_path.stem
    slide_dir = OUTPUT_DIR / slug
    slide_dir.mkdir(parents=True, exist_ok=True)

    total = len(slides)
    generated = []

    for i, slide in enumerate(slides):
        slide_type = classify_slide(slide["title"], i, total)
        img = create_slide(slide_type, slide["content"], title=slide["title"])

        filename = f"slide_{i + 1:02d}_{slide_type}.png"
        filepath = slide_dir / filename
        img.save(filepath, "PNG", quality=95)
        generated.append(filepath)
        print(f"  Created: {filepath.relative_to(PROJECT_ROOT)}")

    print(f"\nGenerated {len(generated)} slides in: {slide_dir.relative_to(PROJECT_ROOT)}/")
    return slide_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_slides.py <path-to-post-markdown>")
        sys.exit(1)

    generate_slides(sys.argv[1])
