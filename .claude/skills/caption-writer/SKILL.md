---
name: caption-writer
description: Write Instagram captions for Prompt Optimizer marketing posts. Use when generating captions, hashtags, or alt text for any post category (did-you-know, autopsy, prompt-pattern, prompt-drop, infographic, user-story). Activates on "write a caption", "generate caption", or when the web UI's background caption generation runs.
---

# Instagram Caption Writer for Prompt Optimizer

Write captions for Prompt Optimizer's Instagram marketing posts. Every caption must follow these rules exactly.

## Before Writing

Read these files first:
1. `config/brand.yaml` - voice, tone, product info
2. `config/icps/solo-builder.yaml` - target audience
3. The prompt template at `prompts/instagram/{category}.md` for category-specific structure

## Absolute Rules (Never Break These)

1. **NEVER use em dashes (--).** No en dashes either. Use commas, periods, colons, or semicolons instead. Restructure the sentence if needed.
2. **NEVER use over complicated vocabulary:** words that the common public might not know.
3. **NEVER pitch the product.** Captions are educational. The reader should feel smarter, not sold to.
4. **No generic AI excitement** like "AI is changing everything!" or "The future is here!"

## Caption Structure (All Categories)

### Line 1: The Hook
- Shows in the Instagram preview (first ~125 chars visible before "...more")
- Must stop the scroll. Use a question, provocative statement, or surprising claim
- Short. One sentence max
- Examples: "Your AI is ignoring the middle of your prompt." / "You asked for 5 steps. You got 12."

### Body: 1-2 Paragraphs
- Explain the WHY behind the topic. Be specific and technical but accessible
- Reference specific model behavior (ChatGPT, Claude, Gemini, Cursor)
- Use concrete examples the reader recognizes from their own workflow
- Write for someone who uses AI daily but hasn't studied prompt engineering
- Keep paragraphs to 2-4 sentences each

### Actionable Takeaway: 1 Sentence
- Tell the reader exactly what to do differently
- Start with "Try it now:" or "Next time you..." or a direct instruction
- Must be immediately actionable, not theoretical

### CTA: 2-3 Lines
The CTA must feel like a NATURAL extension of the lesson, not an ad bolted on at the end. Structure:
1. **Save/engage line** (optional): drive saves or comments
2. **Bridge line**: connect the post topic to what Prompt Optimizer does for this specific problem. The reader should think "oh, that's useful" not "oh, an ad." Write it as a continuation of the insight, not a sales pitch
3. **Link line**: platform-specific (Instagram: "Link in bio." / X: weave the URL into the bridge sentence)

**NEVER just append** "Prompt Optimizer (https://www.promptoptimizr.com/)" as a standalone line. That reads like spam. Always weave it into a sentence that connects to the post's lesson.

**Instagram examples:**
```
Save this for your next Claude session.

Prompt Optimizer rewrites your prompts with the right structure for each model, so you don't have to memorize which format works where. One click, inside your chat window. Link in bio.
```
```
Drop a comment if you've hit the regenerate loop before.

Prompt Optimizer builds the constraints, role frames, and format locks into your prompt automatically. No more guessing what the model needs to hear. Link in bio.
```

**X examples:**
```
Prompt Optimizer does this rewrite for you, matched to whichever model you're using. Try it free: https://www.promptoptimizr.com/
```

**LinkedIn examples:**
```
This is exactly the kind of optimization Prompt Optimizer handles automatically. It restructures your prompt for the specific model you're using, so Claude gets XML, ChatGPT gets Markdown, and Cursor gets file references. No manual reformatting.

Try it free: https://www.promptoptimizr.com/
```

## Voice Rules

- **Confident, technical but accessible, slightly irreverent**
- Use developer-native language: ship, build, debug, iterate, prompt, token
- Short, punchy sentences for impact. Mix sentence lengths
- Make the reader feel smart, not talked down to
- Self-deprecating humor about the AI struggle lands well
- Write like you've been in the trenches, not like a marketer

## Hashtags

Always include 5-10 hashtags, in three tiers:
- 3-5 high-volume (500K+ posts): #artificialintelligence #chatgpt #promptengineering #aitools #machinelearning
- 1-3 mid-volume (50K-500K): #prompttips #aitips #promptdesign #buildwithAI #solodev
- 1-2 niche (under 50K): model-specific or topic-specific tags

Format: space-separated on a single line, e.g. `#tag1 #tag2 #tag3`

## Alt Text

One paragraph describing the image for screen readers:
- Background color
- Text content (what it says)
- Layout and visual elements
- Branding (@PROMPTOPTIMIZER handle)

## Category-Specific Notes

### Did You Know
- Hook: Restate or tease the fact as a question
- Body: Explain the technical "why" behind the fact. 2-3 sentences
- End with: "Save this for your next [model] session."

### Prompt Autopsy
- Hook: Reference the bad prompt's core failure
- Body: Explain the language mismatch between what the user typed and what the model needed
- End with: "Save this carousel for your next debugging session."

### Prompt Pattern
- Hook: Provocative statement about why most people get this wrong
- Body: Explain the pattern's core insight and why it works. Include a quick example
- End with: "Save this for your next prompting session." or "Which pattern should we cover next?"

### Prompt Drop
- Hook: State what this prompt does and for which model
- Body: Explain why this prompt structure works for this specific model
- End with: "Save this prompt. Use it next time you need to [task]."

### User Story
- Hook: The problem/struggle the user faced
- Body: Brief narrative of the transformation. Third person, proper sentences
- End with: "What's your prompt optimization story?"

### Infographic
- Hook: The key insight from the infographic
- Body: One deep paragraph expanding on the data/framework
- End with: "Save this cheat sheet."

## Example Caption (Did You Know)

```
Your AI is ignoring the middle of your prompt.

Stanford researchers tested how language models handle long prompts and found a U-shaped attention curve. Information at the beginning and end gets processed accurately, but anything buried in the middle sees a 30%+ performance drop. In some tests with 20+ documents, GPT-3.5 actually performed worse than having no context at all when the answer was in the middle.

This means prompt structure matters more than prompt length. Put your most critical instructions at the very beginning or very end. Never bury your key constraint in paragraph three.

Save this for your next long prompt session.
```

Notice: no em dashes, educational tone, specific data, actionable takeaway.

## Platform Adaptations

When writing for platforms other than Instagram, adapt the caption to that platform's ideal format while keeping all the rules above.

### Instagram
- **Ideal length:** 800-1500 characters (sweet spot for engagement)
- **Hard limit:** 2200 characters
- **Hook visibility:** First ~125 characters show before "...more"
- **Format:** Hook → blank line → Body (1-2 paragraphs) → blank line → Actionable takeaway → blank line → CTA → blank line → Hashtags
- **Hashtags:** 5-10, space-separated on a single line after the caption
- **Line breaks:** Use blank lines between hook, body, takeaway, and CTA for readability

### X (Twitter)
- **Ideal length:** 200-280 characters (single tweet)
- **Hard limit:** 280 characters per tweet
- **Format:** One punchy insight or bold claim. End with the CTA woven naturally into the last sentence
- **CTA:** Weave the link naturally into the closing sentence. NEVER just append "Prompt Optimizer (url)" at the end. Instead write something like: "Prompt Optimizer handles this automatically, try it free: https://www.promptoptimizr.com/" or "That's what Prompt Optimizer does in one click: https://www.promptoptimizr.com/"
- **Hashtags:** 0-2 max, at the end only
- **Thread option:** For deeper content, write a 3-5 tweet thread. First tweet is the hook. Number them (1/, 2/, etc.). Each tweet under 280 chars

### LinkedIn
- **Ideal length:** 1000-1800 characters
- **Hard limit:** 3000 characters
- **Hook visibility:** First ~210 characters show before "...see more"
- **Format:** Single-sentence paragraphs with blank lines between them (LinkedIn rewards whitespace). Hook on its own line, then body as short paragraphs, then takeaway, then CTA
- **Hashtags:** 3-5 at the very end, each on its own line. Use professional tags: #PromptEngineering #AIProductivity #SoftwareDevelopment
- **Tone shift:** Slightly more professional than Instagram. First person ("I" / "We") works well. Frame insights as lessons learned
