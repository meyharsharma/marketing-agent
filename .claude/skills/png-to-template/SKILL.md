---
name: png-to-template
description: >
  Convert reference PNG images into production-ready HTML/CSS carousel or single-image templates
  for the marketing content pipeline. Use this skill whenever the user provides reference PNGs,
  mockups, or screenshot designs and wants to create a new template category, rebuild an existing
  template, or match a visual design as HTML. Activates on phrases like "convert this PNG to a
  template", "create a template from this design", "make this into HTML", "new category template",
  or when reference images are provided alongside template creation intent. Also use when the user
  drops PNGs and says things like "replicate this", "match this design", or "build slides like these".
---

# PNG to Template

Convert reference PNG screenshots into pixel-accurate HTML/CSS templates for the post rendering pipeline.

## What This Skill Does

Takes one or more reference PNG images showing a finished slide design and produces:
- `templates/{category}.yaml` — slide type definitions, dimensions, and placeholder schema
- `templates/{category}/` directory containing:
  - One `.html` file per slide type
  - `base.css` — shared fonts, colors, reset, design tokens
  - `sample_content.yaml` — example content matching the reference
- Playwright verification confirming the output matches the reference

Works for both single-image posts and multi-slide carousels.

## Step-by-Step Process

### 1. Collect Inputs

Ask the user for:
- **Reference PNGs**: The screenshot(s) of the design to replicate. Can be a single image or multiple carousel slides.
- **Category name**: What to call this template (e.g., `prompt-drop`, `daily-tip`). Used for filenames and directory names.
- **Which slides repeat**: If it's a carousel, ask which slide type(s) can have variable count (e.g., "the middle step slides can repeat 1-4 times").

If the user has already provided PNGs or context in the conversation, extract what you can and confirm rather than re-asking.

### 2. Analyze the Reference PNGs

Read each PNG with the Read tool. For every slide, extract:

**Layout & Dimensions**
- Overall dimensions (almost always 1080x1080 or 1080x1350)
- Whether it's landscape, square, or portrait
- Grid structure: how the slide is divided into zones (header area, body area, footer, sidebar)
- Absolute positions of each text block and decorative element

**Typography**
- Font families (match to fonts available in `fonts/` directory; list them with `ls fonts/`)
- Font weights (bold, regular, light)
- Font sizes in px (estimate from the image proportions — a 1080px-wide slide gives you a reference)
- Line heights
- Text alignment (left, center, right)
- Text transforms (uppercase, lowercase, none)

**Colors**
- Background color(s) or gradient
- Text colors for each element (heading, body, accent)
- Highlight/accent colors (e.g., red pill backgrounds behind keywords)
- Any transparency/opacity values

**Visual Elements**
- Background images or patterns (solid color, gradient, PNG background, grid pattern)
- Decorative elements (arrows, swooshes, dots, lines, bookmarks, icons)
- Borders, rounded corners, shadows
- Brand elements (logo, handle text, URL)

**Content Zones**
- Identify each distinct text region and what role it plays (heading, subheading, body, caption, CTA, step number, quote)
- Note which text varies per post (these become `{{placeholders}}`)
- Note which text is static/brand (these get hardcoded)

### 3. Check Available Fonts

```bash
ls fonts/
```

Match the fonts you see in the reference to what's available. If no exact match exists, pick the closest available font and note it. Common mappings:
- Bold sans-serif headings → Poppins-Bold, Montserrat-Bold, PaytoneOne
- Body text → Poppins-Regular, OpenSans, Inter
- Condensed → OpenSansCondensed

### 4. Study Existing Templates for Patterns

Before writing anything, read 1-2 existing templates that are closest in style to the reference design. This ensures consistency with the codebase conventions.

```
templates/{similar-category}.yaml
templates/{similar-category}/base.css
templates/{similar-category}/{slide-type}.html
```

Key conventions to follow:
- HTML files are minimal: `<!DOCTYPE html>`, link to `base.css`, inline `<style>` for slide-specific overrides, `<body>` with a `.slide` container
- CSS uses absolute positioning (`position: absolute; top: Xpx; left: Xpx;`) for precise placement
- Placeholders use `{{double_braces}}` syntax
- Fonts reference `../../fonts/FontName.ttf` via `@font-face`
- Background images use relative `url('bg_name.png')` in inline `<style>`
- The `.slide` class always has `width`, `height`, `position: relative`, `overflow: hidden`, `background-size: cover`

### 5. Write the Template Files

#### 5a. `base.css`

```css
@font-face {
  font-family: 'FontName';
  src: url('../../fonts/FontName-Bold.ttf') format('truetype');
  font-weight: 700;
}
/* ... more @font-face declarations as needed */

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  width: {width}px;
  height: {height}px;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

.slide {
  width: {width}px;
  height: {height}px;
  position: relative;
  overflow: hidden;
  background-size: cover;
  background-position: center;
  font-family: 'FontName', sans-serif;
}

/* Shared text styles, brand elements, design tokens */
```

Put only styles shared across ALL slide types in base.css. Slide-specific styles go in each HTML file's inline `<style>`.

#### 5b. Individual HTML Files (one per slide type)

Each HTML file follows this structure:

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="base.css">
  <style>
    .slide { background: #191919; /* or background-image: url('bg_cover.png'); */ }
    /* All positioning and styling for THIS slide type only */
  </style>
</head>
<body>
  <div class="slide">
    <!-- Content elements with {{placeholders}} -->
  </div>
</body>
</html>
```

Guidelines:
- Use absolute positioning for every element. The renderer takes a screenshot at exact pixel dimensions — CSS grid/flexbox is fine for internal layout of a zone, but the zone itself should be absolutely positioned.
- Put `{{placeholders}}` for all content that changes per post.
- Hardcode brand elements (handle, URL, logo references).
- For inline highlighted text (word with colored background), use the pattern: `{{before}} <span class="red">{{highlight}}</span> {{after}}`
- For repeating slides that need a step number, include `{{step_number}}` placeholder.

#### 5c. `{category}.yaml`

```yaml
name: Display Name
description: One-line description of what this template is for
category: {category}
platform: instagram

dimensions:
  width: 1080
  height: 1350  # or 1080

slides:
  - type: cover          # Maps to cover.html
    name: "Cover Slide"
    placeholders:
      heading:
        description: "Main heading text"
        required: true
        example: "Example heading"
      body:
        description: "Body text below heading"
        required: false
        example: ""

  - type: step            # Maps to step.html
    name: "Content Step"
    repeat: true           # Enables step_1, step_2, etc.
    min_count: 1
    max_count: 4
    placeholders:
      heading:
        description: "Step heading"
        required: true
        example: "Step text"

  - type: closing          # Maps to closing.html
    name: "Closing Slide"
    placeholders:
      cta:
        description: "Call to action text"
        required: false
        example: "Save this post"
```

For single-image templates, the `slides` array has just one entry with `repeat: false`.

#### 5d. `sample_content.yaml`

Create sample content that matches what's shown in the reference PNGs:

```yaml
cover:
  heading: "Text from the reference"
  body: "Body text from reference"

step_1:
  heading: "First step text"
  body: "First step body"

step_2:
  heading: "Second step text"
  body: "Second step body"

closing:
  cta: "Save and bookmark this"
```

### 6. Extract or Create Background Assets

If the reference uses a background image (not just a solid color):

**Option A — The background is a reusable PNG with text overlaid**
The background contains decorative elements (swooshes, lines, dots, gradients) but NOT the content text. These backgrounds should be saved as `bg_{slide_type}.png` in the template directory. If the same background is used by another category, reference it with a relative path: `url('../other-category/bg_name.png')`.

**Option B — The background is pure CSS**
Replicate with CSS gradients, borders, and pseudo-elements. This is preferred when possible because it's more maintainable.

If the user has separate background PNGs, ask them to place the files in `templates/{category}/` and name them `bg_{slide_type}.png`.

### 7. Render and Verify with Playwright

After writing all files, render with the sample content:

```bash
python3 scripts/render_carousel.py templates/{category}.yaml templates/{category}/sample_content.yaml test-{category}
```

Then visually compare each rendered slide against the reference:

1. Read the rendered PNGs from `generated_slides/test-{category}/`
2. Read the original reference PNGs
3. Compare side-by-side, checking:
   - Text positioning (within ~10px of reference)
   - Font sizes and weights match
   - Colors match (exact hex values)
   - Decorative elements are present and correctly placed
   - Overall proportions and spacing feel right
   - Nothing is cut off, overlapping, or misaligned

If there are discrepancies, fix the CSS and re-render. Repeat until the output is a close match.

### 8. Clean Up

```bash
rm -r generated_slides/test-{category}/
```

Remove test renders after verification is complete.

## Common Pitfalls

**Font sizing**: When estimating font sizes from a reference PNG, remember the slide is 1080px wide. A heading that spans about half the width at ~10 characters is roughly 90-100px. Body text that's comfortable to read on a phone is usually 28-38px.

**Background PNGs in wrong directory**: Always place `bg_*.png` files in the same directory as the HTML files that reference them. Never use cross-category references for NEW templates — only existing templates may reference other categories' assets.

**Forgetting the auto-scale script**: For slides with variable-length content, consider adding an inline `<script>` that shrinks the font if text overflows its container. Look at existing templates (e.g., `templates/autopsy/hook.html`) for the pattern.

**Placeholder naming**: Use descriptive names that match the content role: `heading`, `body`, `highlight`, `cta`, `step_number`, `quote`. For the inline-highlight pattern, use `before`, `highlight`, `after`.

**Testing with real content**: After the template passes with sample content, ask the user if they want to test with real post content to verify edge cases (long text, short text, special characters).
