# Prompt Infographic — Instagram Single Image Generation Instructions

## Before Generating

Read these config files and use their data throughout:
- `config/brand.yaml` — product info, voice, differentiators
- `config/platforms/instagram.yaml` — platform constraints and visual style
- `config/icps/{icp}.yaml` — target audience profile

## What You're Creating

A single Instagram image (1080x1350, portrait) packed with reference-worthy information: cheat sheets, comparison charts, tip compilations, or frameworks. Dense but readable. Designed to be saved and returned to.

## NotebookLM Integration

These infographics are research-backed. Before generating content:

1. **Source material should come from NotebookLM.** The user maintains a NotebookLM notebook with:
   - Prompt Optimizer's model-specific guides (from the codebase)
   - OpenAI, Anthropic, Google model documentation
   - Prompt engineering research and benchmarks
2. **Query NotebookLM** for the specific topic to get factual, research-backed content.
3. **Format the NotebookLM output** into the infographic structure with brand voice applied.

If NotebookLM content is not provided, generate from the PO codebase knowledge (model guides, optimization rules).

## Infographic Types

### Type 1: Cheat Sheet
A reference card with 5-10 tips, rules, or techniques for a specific topic.
- Numbered or bulleted list format
- Each item: bold label + one-line explanation
- Example: "The One-Shot Prompt Checklist", "XML Tags Cheat Sheet for Claude"

### Type 2: Comparison Chart
Side-by-side comparison of 2-3 models, techniques, or approaches.
- Column layout with headers
- Key differences highlighted with color
- Example: "ChatGPT vs Claude vs Gemini: Prompt Structure Compared"

### Type 3: Framework / Diagram
A visual framework showing how prompt components relate to each other.
- Layered, stacked, or flowchart layout
- Clear hierarchy with labeled sections
- Example: "The Prompt Engineering Stack", "The Prompt Optimization Flowchart"

### Type 4: Data-Backed Insight
A single insight supported by data or benchmarks.
- Large stat or number as the centerpiece
- Supporting context below
- Example: "The 37% Rule: How Structure Saves Tokens"

## Output Structure

### Image Content

**Title** (large heading, coral, uppercase):
The infographic title — clear, specific, save-worthy.

**Sections** (structured content):
The body content organized by infographic type. Must be readable at phone size.
- Use clear section headers
- Keep individual items to one line where possible
- Use numbered lists for ordered content, bullets for unordered

**Branding** (subtle):
Handle + sidebar. No product pitch on the image.

### Caption

1. **Hook**: Why this reference is worth saving.
2. **Context** (2-3 sentences): The "so what" — why this information matters for daily AI use.
3. **Deep insight** (1-2 sentences): One point from the infographic expanded.
4. **CTA**: "Save this as a reference." or "Screenshot this cheat sheet."

### Hashtags

15 hashtags (5 high-volume, 5 mid-volume, 5 niche).

### Alt Text

Full description of the infographic: title, all text content, layout, colors.

## Quality Rules

- Information density is high but readability is non-negotiable — test at phone size mentally
- Every fact must be technically accurate
- NotebookLM-sourced content is preferred for credibility
- No product pitching — the information is the value
- Portrait format (1080x1350) gives more vertical space for dense content
- Use consistent section styling — don't mix formatting approaches within one infographic
