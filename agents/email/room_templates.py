# agents/email/room_templates.py
# Room-specific email prompt templates
# Extracted from prompt_template_builder.py to maintain 700-line file limit
# Contains the 7-component templates for each room + format combination

from __future__ import annotations


# ============================================================================
# Email Format Types
# ============================================================================

EMAIL_FORMAT_FIELD_NOTE = "field_note"
EMAIL_FORMAT_STANDARD = "standard"


# ============================================================================
# Problem Room Templates — Field Note format (default)
# ============================================================================

PROBLEM_ROOM_FIELD_NOTE_TEMPLATES: dict[str, str] = {
    "subject_guidance": """
Create a subject line that:
- MUST start with "Field Note:" prefix
- Names a specific symptom, mistake, or hidden cost
- Under 60 characters total
- No hype words: free, quick call, resource, checklist, limited time, exclusive
- Examples:
  - "Field Note: the weeks-later query tax"
  - "Field Note: when lead quality is a clarity problem"
  - "Field Note: the metric that predicts rework"
""",

    "opening_style": """
Use this exact structure:

Hi {first_name} —

I'm {sender_name}.

I send one short note like this each week on {problem_space}. If it's not useful, reply "stop" and I'll disappear.

Rules:
- No other greeting style. No "Hope you're well." No "I'm reaching out."
- The opt-out line goes near the top, not the bottom.
- First name only for the sender (unless client requires more).
""",

    "pain_framing": """
Structure the value block with these EXACT labels, in this order:

**What's happening:** (1 sentence, plain English, describing the real-world problem)
**The real cause:** (1 sentence that reframes: "this looks like X but is actually Y")
**Quick test (2 minutes):** (1 bullet, max 2. Immediately runnable, non-obvious)
**What to do next (small move):** (2 bullets, max 3. Practical THIS WEEK. No pitch.)

Rules:
- "What's happening" and "The real cause" must be ONE SENTENCE each.
- Quick test must be something a real person can do in 2 minutes.
- Small moves must be actionable this week, not "consider" or "think about."
- Every item must be grounded in the article content provided.
- Include one expert distinction: a misdiagnosis, tradeoff, or reframe.
""",

    "value_positioning": """
Position value through specificity, not claims.
- No "this is helpful" or "high value" or "insightful."
- Be helpful by giving a clear test, metric, or action.
- Use the prospect's industry context to make examples concrete.
- Keep it operational/process oriented.
- DO NOT mention any company, product, or service.
- DO NOT use "we" or "our" language.
""",

    "content_integration": """
If a content link is provided, add it as a single optional line AFTER the value block:

"If you want the longer breakdown, here it is (no signup): {url}"

Rules:
- The email MUST deliver full value without clicking.
- The link is supplementary, never gated, never required.
- Never say "click here to get the full version."
- Never require a reply to get the resource.
""",

    "credibility_elements": """
Signal expertise through the quality of the insight, not through claims.
- No "I work with leaders like you."
- No "we've helped 100+ companies."
- No testimonials or social proof.
- Let the specificity of the quick test and reframe do the work.
""",

    "cta_approach": """
Close with EXACTLY:

No need to reply. Hope it helps.

{sender_name}

Rules:
- No ask. No call. No meeting request. No question that requires a reply.
- No "open to chat?" No "would love to connect."
- No "I'll follow up" or multi-touch framing.
- This is a note, not an outreach sequence.
""",
}


# ============================================================================
# Problem Room Templates — Standard format (non-Field Note)
# ============================================================================

PROBLEM_ROOM_STANDARD_TEMPLATES: dict[str, str] = {
    "subject_guidance": """
Create a subject line that:
- Focuses on the PROBLEM, not solutions
- Uses curiosity or recognition ("Is this happening to you?")
- Under 50 characters
- No company name or product references
""",

    "opening_style": """
Open with empathy and recognition:
- Acknowledge the reader's likely situation
- Use "you" language, not "we" language
- Keep it under 2 sentences
- No flattery, no false familiarity
""",

    "pain_framing": """
Describe the problem through the buyer's lens:
- Name symptoms they likely recognize
- Quantify impact where possible (time, money, risk)
- Use their industry language
- DO NOT name your company or solutions
- DO NOT use "we" or "our" language at all
""",

    "value_positioning": """
Position the content as a thinking tool:
- Frame the linked resource as educational
- "Others in {industry} have found..."
- "This research suggests..."
- Pure third-person perspective
""",

    "content_integration": """
Present the content link as a helpful resource:
- "Here's an article that breaks this down: {url}"
- Never gate it or require a form fill
- The email should provide value even without clicking
""",

    "credibility_elements": """
Build credibility through insight, not claims:
- Share a non-obvious observation about the problem
- Reference industry-level data if available
- DO NOT mention your company, clients, or track record
""",

    "cta_approach": """
Close without asking for anything:
- "Worth a read if this resonates."
- No meeting requests, no "let's chat"
- No reply-required questions
- Sign off simply with sender name
""",
}


# ============================================================================
# Solution Room Templates
# ============================================================================

SOLUTION_ROOM_TEMPLATES: dict[str, str] = {
    "subject_guidance": """
Create a subject line that:
- Hints at a solution approach or framework
- Creates curiosity about methodology
- Under 50 characters
- May reference "how" or "why" framing
""",

    "opening_style": """
Open with shared understanding:
- Acknowledge the challenge the reader is addressing
- Reference the general problem space
- Keep it brief (1-2 sentences)
- May use "organizations like yours" softly
""",

    "pain_framing": """
Frame the pain as a solvable challenge:
- Reference the problem as something they've likely identified
- Transition toward approaches and frameworks
- May reference how others have addressed similar issues
- Still educational, not promotional
""",

    "value_positioning": """
Position solution approaches educationally:
- Compare different approaches (build vs buy, outsource vs internal)
- Highlight trade-offs honestly
- May softly reference "our experience" or "organizations we work with"
- NO pricing language
- NO aggressive positioning
""",

    "content_integration": """
Present content as a practical guide:
- "This guide walks through the approach: {url}"
- "Here's a case study that shows how this played out: {url}"
- Frame as educational, not promotional
""",

    "credibility_elements": """
Build credibility through relevant experience:
- May reference case studies or anonymized examples
- May mention industry expertise softly
- Focus on outcomes and lessons learned
- Still avoid hard sells or superlatives
""",

    "cta_approach": """
Soft engagement invitation:
- "Happy to share more if this is something you're exploring."
- "Worth a look if your team is evaluating approaches."
- No hard demo requests
- No pricing discussions
""",
}


# ============================================================================
# Offer Room Templates
# ============================================================================

OFFER_ROOM_TEMPLATES: dict[str, str] = {
    "subject_guidance": """
Create a subject line that:
- Speaks to specific outcomes or results
- May reference concrete benefits
- Under 50 characters
- Can be more direct and specific
""",

    "opening_style": """
Open with confidence and relevance:
- Reference the prospect's likely stage of evaluation
- Acknowledge they may be comparing options
- Be direct but not pushy
""",

    "pain_framing": """
Frame the pain in terms of cost of inaction:
- Quantify what the problem costs (time, money, risk)
- Reference the urgency if genuine signals exist
- Connect to business outcomes
""",

    "value_positioning": """
Position your specific offering:
- May discuss company services directly
- Reference ROI, outcomes, and timelines
- May include pricing context if appropriate
- Still maintain helpful, advisory tone
""",

    "content_integration": """
Present content as decision-support:
- "Here's a detailed breakdown of how this works: {url}"
- "This shows the ROI analysis: {url}"
- Can be more promotional in framing
""",

    "credibility_elements": """
Leverage full credibility toolkit:
- Named case studies (with permission)
- Specific metrics and outcomes
- Industry recognition
- Relevant certifications or partnerships
""",

    "cta_approach": """
Clear, direct call to action:
- May request a meeting or demo
- "Would a 20-minute walkthrough be useful?"
- "I can share a proposal tailored to your situation."
- Direct but not aggressive
- STILL no urgency/scarcity tactics
""",
}


# ============================================================================
# Word Count Instructions (embedded in prompts)
# ============================================================================

WORD_COUNT_INSTRUCTIONS: dict[str, str] = {
    EMAIL_FORMAT_FIELD_NOTE: """
## LENGTH CONSTRAINT (NON-NEGOTIABLE)
Target: 110-150 words (NOT including greeting, signature, or link line).
Absolute max: 170 words (excluding greeting/signature/link).
- "What's happening" = 1 sentence
- "The real cause" = 1 sentence
- "Quick test" = 1 bullet (max 2 if unavoidable)
- "What to do next" = 2 bullets (max 3 if unavoidable)
Prefer DELETING over rephrasing. Keep only what changes meaning.
""",

    EMAIL_FORMAT_STANDARD: """
## LENGTH GUIDANCE
- Problem Room: 150-200 words body
- Solution Room: 200-300 words body
- Offer Room: 200-350 words body
Keep it scannable. Short sentences. Short paragraphs.
""",
}


# ============================================================================
# Signal Firewall Instructions (embedded in prompts)
# ============================================================================

SIGNAL_FIREWALL_INSTRUCTIONS = """
## CRITICAL: Private vs Public Signal Rules

You have been given prospect context to help you write a relevant email.
Some of this context is PRIVATE (used only to choose the topic and angle)
and some is PUBLIC (safe to reference in the email).

PRIVATE — DO NOT MENTION IN THE EMAIL:
- Pages they visited on any website
- Content they consumed or downloaded
- Visit count, timing, or recency
- Lead score or room classification
- Engagement signals or intent data
- URLs previously sent to them
- Any phrase like "based on your interest," "I noticed you were reading,"
  "based on your activity," or "when you were on our site"

PUBLIC — SAFE TO REFERENCE:
- Company name
- Industry
- Job title / role
- Company size (as scale-aware wording, not exact employee counts)
- Location (if relevant)
- Publicly known initiatives

Use PRIVATE signals to choose what to write about.
Use PUBLIC context to make it feel written for their world.
If you removed the company name, the email should still clearly fit this role + industry.
"""
