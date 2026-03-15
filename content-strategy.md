# Prompt Optimizer — Instagram Content Strategy

## Posting Cadence

**3 posts per day, 7 days a week = 21 posts/week**

| Slot | Time | Format | Effort |
|------|------|--------|--------|
| **Morning (8-9am)** | Scroll-stopper | Single image | Low |
| **Afternoon (12-1pm)** | Deep-dive | Carousel (5-7 slides) | High |
| **Evening (6-7pm)** | Utility / social proof | Single image or carousel | Medium |

---

## Content Categories

### 1. Prompt Autopsy (carousel — 7 slides)
**Slot:** Afternoon
**Frequency:** 2-3x per week
**Template:** `templates/autopsy/`

Take a real, bad prompt and dissect it slide by slide. Show what the model "hears," isolate each failure pattern, then reveal the optimized version from Prompt Optimizer.

**Content structure:**
- Slide 1: Bad prompt + hook line (coral bg)
- Slide 2: What the model heard (cream bg)
- Slides 3-5: Dissection — one failure per slide (black bg)
- Slide 6: Optimized prompt from user (coral bg)
- Slide 7: Payoff line (cream bg)

**Why it works:** Carousels have the highest save rate. Each autopsy demonstrates the core thesis — model-aware optimization — without feeling like an ad.

**Content bank:**
| # | Bad Prompt | Hook |
|---|-----------|------|
| 1 | "fix my code" | "You called a mechanic and said 'it's broken.'" |
| 2 | "write me a landing page" | "You typed 6 words. The model guessed 47 things." |
| 3 | "make this better" | "5 models. 5 interpretations. All wrong." |
| 4 | "explain this code" | "You pasted 200 lines. The model explained all of them. You needed line 47." |
| 5 | "write unit tests for my app" | "This prompt produces tests that test nothing." |
| 6 | "help me debug this" | "It's 2am. You've hit regenerate 4 times." |
| 7 | "summarize this article" | "The model summarized everything. You needed the one insight." |
| 8 | "create a marketing plan" | "You asked for a plan. You got a Wikipedia article." |
| 9 | "refactor this function" | "Refactor how? Faster? Cleaner? More readable? Pick one." |
| 10 | "generate test data" | "The model generated 100 rows of nonsense." |
| 11 | "write a README" | "Your README reads like it was written by someone who never used the product." |
| 12 | "build me a dashboard" | "A dashboard for whom? Showing what? Updated how often?" |

---

### 2. Did You Know (single image)
**Slot:** Morning
**Frequency:** 3-4x per week
**Template:** `templates/did-you-know/`

Surprising facts about how AI models actually process prompts. Short, punchy, shareable. One fact per image.

**Visual style:** Black background, coral accent, large text. One sentence fact + one sentence explanation.

**Content bank:**
| # | Fact | Detail |
|---|------|--------|
| 1 | GPT-5 reads constraints backwards | It prioritizes the LAST instruction in your prompt, not the first |
| 2 | Claude uses XML, not Markdown | Claude responds better to `<task>` tags than `# Task` headers |
| 3 | Gemini drops early constraints | Put critical rules at the END — Gemini weights end-positioned content heaviest |
| 4 | "Don't" doesn't work on Claude | Claude responds better to positive framing: "do X" not "don't do Y" |
| 5 | Cursor ignores role prompts | "You are a senior developer" does nothing in Cursor — it already is one |
| 6 | Adding 4 words saves 37% tokens | A role frame + output format reduces token usage dramatically |
| 7 | Claude Code's #1 technique | "Run tests after changes" — one line turns it from assistant to engineer |
| 8 | "Make it better" has 5 meanings | Faster? Cleaner? Shorter? Different tone? For whom? The model picks randomly |
| 9 | Temperature 0.5 is the sweet spot | High enough for creativity, low enough for consistency |
| 10 | Bounded quantities beat open-ended | "3-5 key areas" outperforms "cover the key areas" every time |
| 11 | GPT-5 prefers Markdown headers | Structure with # headers, not plain text paragraphs |
| 12 | Claude wants WHY, not just WHAT | "Avoid jargon because the reader is a first-time founder" beats "don't use jargon" |
| 13 | Same prompt ≠ same result | The same prompt structured differently for each model produces dramatically different outputs |
| 14 | Your prompt has an action verb problem | Most tools silently downgrade "Build" to "Outline" — your intent gets lost |
| 15 | Cursor needs @-references | @filename.ts gives Cursor context that plain English never will |

---

### 3. Daily Prompt Drop (single image)
**Slot:** Morning or Evening
**Frequency:** 2-3x per week
**Template:** `templates/prompt-drop/`

One polished, ready-to-use prompt template. Screenshot-worthy. Optimized for a specific model. People save these.

**Visual style:** Coral background, black/white text. The prompt displayed cleanly with the target model tagged.

**Content bank:**
| # | Task | Target Model | Prompt Preview |
|---|------|-------------|----------------|
| 1 | REST API endpoint | ChatGPT | "You are a senior backend dev. Build a REST endpoint for [X] with input validation, error handling, rate limiting, and tests." |
| 2 | Code review | Claude | `<task>Review this PR for bugs, security issues, and performance.</task><constraints>Flag severity as P0/P1/P2. Max 5 findings.</constraints>` |
| 3 | Debug a crash | Cursor | "Goal: Fix the crash in @auth/login.ts. Error: [paste]. Constraints: Don't change the public API." |
| 4 | Landing page copy | ChatGPT | "You are a conversion copywriter for B2B SaaS. Write hero section copy for [product]. Include: headline (under 10 words), subheadline, 3 bullet points, CTA." |
| 5 | Database schema | Claude | `<role>Senior database architect</role><task>Design a normalized schema for [domain]</task><format>SQL CREATE statements + ER description</format>` |
| 6 | Email onboarding | ChatGPT | "Write a 5-email onboarding drip sequence for [product]. Each email: subject line, preview text, body (under 150 words), CTA." |
| 7 | Refactor function | Claude Code | "Refactor @utils/parser.ts to use async/await instead of callbacks. Verify: run tests, ensure no type errors." |
| 8 | Technical blog post | Claude | `<role>Developer advocate</role><task>Write a 1500-word tutorial on [topic]</task><constraints>Include code snippets, avoid jargon, target intermediate devs</constraints>` |
| 9 | Unit test generation | Cursor | "Goal: Add unit tests for @services/payment.ts. Cover: happy path, edge cases, error states. Framework: Jest." |
| 10 | Data analysis | Gemini | `<role>Data analyst</role><task>Analyze this dataset for trends</task><output_format>3-5 key insights, each with supporting data points</output_format><final_instruction>Prioritize actionable findings over interesting-but-useless correlations</final_instruction>` |

---

### 4. Prompt Pattern (carousel — 5-6 slides)
**Slot:** Afternoon
**Frequency:** 2x per week
**Template:** `templates/prompt-pattern/`

Teach one reusable prompting technique. Educational, deep, save-worthy. Each pattern is a transferable skill.

**Content structure:**
- Slide 1: Pattern name + hook (coral bg)
- Slide 2: The problem this pattern solves (cream bg)
- Slide 3-4: How the pattern works + example (black bg)
- Slide 5: Before vs after (black bg)
- Slide 6: When to use it (cream bg)

**Content bank:**
| # | Pattern Name | Core Insight |
|---|-------------|-------------|
| 1 | Bounded Quantities | "3-5 areas" beats "cover everything" — fewer tokens, better output |
| 2 | The Role Frame | Adding "You are a [role]" changes the model's entire reasoning approach |
| 3 | End-Positioning | GPT-5 prioritizes constraints at the END of the prompt |
| 4 | Reasoning-Based Constraints | Tell Claude WHY, not just WHAT — it follows reasoning, not orders |
| 5 | Verification-First (Claude Code) | "Run tests" is the highest-leverage line in an agentic prompt |
| 6 | Output Format Lock | Specifying exact format prevents the model from improvising structure |
| 7 | The Action Verb Rule | Never let a tool downgrade "Build" to "Outline" — intent is sacred |
| 8 | Scope Narrowing | Point to specific files, not "the codebase" — broad scope wastes context |
| 9 | @-Reference Architecture | Cursor needs file references, not English descriptions |
| 10 | The Anti-Pattern Slide | "Do X because Y" beats "Don't do Z" on every model |
| 11 | Context Injection | "Write copy" → "Write copy for B2B SaaS targeting CTOs" — 4 words, 10x better |
| 12 | Step Count Calibration | 3-4 steps for simple tasks, 5-6 for medium, 7-9 for complex — never more |

---

### 5. Prompt Infographic (single image)
**Slot:** Evening
**Frequency:** 2-3x per week
**Template:** `templates/infographic/`

Cheat sheets, tip compilations, comparison charts, frameworks. Dense, reference-worthy single images designed to be saved and shared. High information density.

**Visual style:** 1080x1350 (portrait), dark background, structured layout with sections/columns/numbered lists. Clean typography hierarchy.

**NotebookLM Integration:**
These infographics are research-backed. Workflow:
1. Feed relevant prompt engineering sources into NotebookLM
2. Use NotebookLM to extract key insights, patterns, and data points
3. NotebookLM generates the structured content (tips, comparisons, frameworks)
4. Content is formatted into the infographic template
5. Rendered via the carousel editor

NotebookLM sources to maintain:
- Model documentation (OpenAI, Anthropic, Google)
- Prompt engineering research papers
- Prompt Optimizer's own model-specific guides (from the codebase)
- Community best practices and benchmarks

**Content bank:**
| # | Infographic Title | Type | NotebookLM Source |
|---|------------------|------|-------------------|
| 1 | "The One-Shot Prompt Checklist" | Checklist | Model guides from PO codebase |
| 2 | "ChatGPT vs Claude vs Gemini: Prompt Structure Compared" | Comparison chart | Model-specific templates |
| 3 | "5 Constraints Every Prompt Needs" | Numbered list | Prompt engineering best practices |
| 4 | "The Prompt Engineering Stack" | Layered diagram | Role → Context → Task → Format → Constraints |
| 5 | "Model-Specific Formatting Rules" | Reference card | PO's model guides |
| 6 | "10 Prompt Anti-Patterns" | List | Common failures from autopsy content |
| 7 | "Token Cost: Structured vs Unstructured" | Data viz | Token reduction data |
| 8 | "Cursor vs ChatGPT: Different Tools, Different Prompts" | Side-by-side | PO Cursor guide |
| 9 | "The Prompt Optimization Flowchart" | Flowchart | Decision tree: which style for which task |
| 10 | "XML Tags Cheat Sheet for Claude" | Reference card | Claude-specific formatting |
| 11 | "Prompt Engineering for Code Generation" | Framework | Dev-specific techniques |
| 12 | "The 37% Rule: How Structure Saves Tokens" | Data-backed | Token analysis |

---

### 6. User Story (carousel — 5-6 slides)
**Slot:** Evening
**Frequency:** 1-2x per week
**Template:** `templates/user-story/`

Real stories of people using Prompt Optimizer to solve a problem. Social proof + educational. Shows the product in action without being an ad.

**Content structure:**
- Slide 1: The problem / struggle (coral bg, hook text)
- Slide 2: What they were doing before (cream bg — the old way)
- Slide 3: The moment they used Prompt Optimizer (black bg — the switch)
- Slide 4: The optimized prompt + result (coral bg — the payoff)
- Slide 5: The takeaway / what changed (cream bg — the lesson)

**Sourcing user stories:**
- Reach out to active users for testimonials
- Monitor social mentions and DMs
- Create a "submit your story" form
- Internal team use cases (dogfooding)
- Beta tester feedback

**Content bank (templates — fill with real stories):**
| # | Persona | Problem | Before → After |
|---|---------|---------|----------------|
| 1 | Solo dev building a SaaS | Spent 20 min per prompt getting code output right | One-shot prompt, shipped feature in half the time |
| 2 | Freelancer writing client proposals | ChatGPT proposals sounded generic | Claude-optimized prompt → personalized, client-specific output |
| 3 | Student writing research paper | Kept getting surface-level summaries | Added bounded quantities + role frame → deep analysis |
| 4 | Content creator writing newsletters | Tone was inconsistent across posts | Style-locked prompt → consistent brand voice every time |
| 5 | Dev team lead reviewing PRs | AI code reviews missed critical issues | Claude XML-structured review prompt → caught P0 bugs |
| 6 | Indie hacker building in public | Cursor prompts weren't producing usable code | Switched from ChatGPT-style to @-reference prompts → working code first try |
| 7 | Founder writing investor updates | ChatGPT outputs felt like homework essays | Optimized prompt with format lock → clean, data-driven updates |
| 8 | Designer prompting for copy | AI copy was generic and off-brand | Added brand context + constraints → on-brand copy |

---

## Weekly Posting Schedule

### Rotation Pattern

| Day | Morning (Single) | Afternoon (Carousel) | Evening (Single/Carousel) |
|-----|-----------------|---------------------|--------------------------|
| **Mon** | Did You Know | Prompt Autopsy | Prompt Infographic |
| **Tue** | Daily Prompt Drop | Prompt Pattern | User Story |
| **Wed** | Did You Know | Prompt Autopsy | Daily Prompt Drop |
| **Thu** | Did You Know | Prompt Pattern | Prompt Infographic |
| **Fri** | Daily Prompt Drop | Prompt Autopsy | User Story |
| **Sat** | Did You Know | Prompt Pattern | Prompt Infographic |
| **Sun** | Daily Prompt Drop | Prompt Autopsy | Did You Know |

### Weekly totals:
- **Did You Know:** 5x/week (Mon AM, Wed AM, Thu AM, Sat AM, Sun EVE)
- **Daily Prompt Drop:** 4x/week (Tue AM, Wed EVE, Fri AM, Sun AM)
- **Prompt Autopsy:** 4x/week (Mon PM, Wed PM, Fri PM, Sun PM)
- **Prompt Pattern:** 3x/week (Tue PM, Thu PM, Sat PM)
- **Prompt Infographic:** 3x/week (Mon EVE, Thu EVE, Sat EVE)
- **User Story:** 2x/week (Tue EVE, Fri EVE)

**Total: 21 posts/week = 3/day**

---

## Content Production Workflow

### Single Image Posts (Did You Know, Daily Prompt Drop, Infographic)
1. Load brand config + ICP profile
2. Pick topic from content bank
3. For infographics: query NotebookLM for research-backed content
4. Generate content YAML with placeholder values
5. Render via: `python3 scripts/render_carousel.py templates/{category}.yaml content.yaml`

### Carousel Posts (Autopsy, Prompt Pattern, User Story)
1. Load brand config + ICP profile + platform config
2. Pick topic from content bank
3. Load prompt template: `prompts/instagram/{category}.md`
4. Generate full post markdown
5. For autopsy: pause for user to provide optimized prompt from Prompt Optimizer
6. Save to `output/instagram/{category}/`
7. Render slides via carousel editor

### NotebookLM Integration (Infographics)
1. Maintain a NotebookLM notebook with prompt engineering sources:
   - Prompt Optimizer model guides (from codebase: model-specific system prompts)
   - OpenAI, Anthropic, Google model documentation
   - Prompt engineering research and benchmarks
2. Before creating an infographic, query NotebookLM:
   - "What are the key differences between prompting ChatGPT vs Claude?"
   - "What data supports structured prompts reducing token usage?"
   - "What are the most common prompt anti-patterns?"
3. Use NotebookLM output as the factual backbone
4. Format into the infographic template with brand voice applied

---

## Templates Required

| Category | Template Dir | Format | Slides | Status |
|----------|-------------|--------|--------|--------|
| Prompt Autopsy | `templates/autopsy/` | Carousel | 7 | Done |
| Did You Know | `templates/did-you-know/` | Single image | 1 | To build |
| Daily Prompt Drop | `templates/prompt-drop/` | Single image | 1 | To build |
| Prompt Pattern | `templates/prompt-pattern/` | Carousel | 5-6 | To build |
| Prompt Infographic | `templates/infographic/` | Single image | 1 | To build |
| User Story | `templates/user-story/` | Carousel | 5 | To build |

---

## Content Metrics to Track

| Metric | Target | Why |
|--------|--------|-----|
| Save rate | >5% | Saves = algo boost. Carousels and cheat sheets drive saves. |
| Share rate | >2% | Shares = new audience. "Did You Know" and infographics drive shares. |
| Comment rate | >3% | Comments = engagement signal. User stories and autopsies drive comments. |
| Follower growth | 200+/week | Consistent 3x/day posting with educational content compounds. |
| Profile visits | Track weekly | Leading indicator of conversion to website/extension. |
