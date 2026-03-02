# config/field_note_spec.py
# Field Note email specification constants
# Extracted from FIELD_NOTE_SPEC_v2.md, VOICE_GUIDE_MEMO.md, EXAMPLES_GOOD.md
# Used by prompt_template_builder.py for Problem Room "Field Note" emails

from __future__ import annotations


# ============================================================================
# Field Note Email Structure
# ============================================================================
# Every Field Note follows this exact scaffold:
# 1. Subject: Field Note: <specific symptom, mistake, or hidden cost>
# 2. Greeting: Hi <First Name> —
# 3. Line 1: I'm <Sender First Name>.
# 4. Line 2: Cadence + opt-out
# 5. What's happening: 1 sentence
# 6. The real cause: 1 sentence (reframe: "looks like X / actually Y")
# 7. Quick test (2 minutes): 1 bullet (max 2)
# 8. What to do next (small move): 2 bullets (max 3)
# 9. Optional link line
# 10. Close: No need to reply. Hope it helps.
# ============================================================================

# Word count limits (excluding greeting, signature, link line)
FIELD_NOTE_TARGET_WORDS: int = 130  # midpoint of 110-150
FIELD_NOTE_MIN_WORDS: int = 110
FIELD_NOTE_MAX_WORDS: int = 170  # absolute max


# ============================================================================
# Angle Library — rotate weekly to avoid repetition
# ============================================================================

FIELD_NOTE_ANGLES: list[dict[str, str]] = [
    {
        "id": "misdiagnosis",
        "label": "Misdiagnosis",
        "description": "It's not X, it's Y. Reframe the problem.",
    },
    {
        "id": "leading_indicator",
        "label": "Leading Indicator",
        "description": "Measure this before surveys or lagging metrics.",
    },
    {
        "id": "workflow_design_bug",
        "label": "Workflow Design Bug",
        "description": "The process causes the problem, not the people.",
    },
    {
        "id": "noise_vs_signal",
        "label": "Noise vs Signal",
        "description": "Reduce low-value work to reveal what matters.",
    },
    {
        "id": "fit_friction",
        "label": "Fit / Friction",
        "description": "Use constraints to increase trust or reduce drag.",
    },
    {
        "id": "stop_doing_this",
        "label": "Stop Doing This",
        "description": "Anti-patterns that feel productive but create waste.",
    },
    {
        "id": "what_good_looks_like",
        "label": "What Good Looks Like",
        "description": "Clear standards, not vague aspirations.",
    },
    {
        "id": "tradeoffs",
        "label": "Tradeoffs",
        "description": "What you gain and lose with each approach.",
    },
    {
        "id": "small_pilot",
        "label": "Small Pilot",
        "description": "Bounded improvement, one service line, 30 days.",
    },
]


# ============================================================================
# Ban List — words/phrases that must never appear in Field Notes
# ============================================================================

FIELD_NOTE_BAN_LIST: list[str] = [
    # Outreach / sales clichés
    "I'm reaching out",
    "reaching out",
    "touch base",
    "circle back",
    "quick call",
    "15 minutes",
    "hop on a call",
    "are you available",
    "following up",
    "just checking in",
    "thought you might find this helpful",
    "value",
    "high-value",
    "insightful",
    "game-changing",
    "unlock",
    "leverage",
    "synergy",
    "streamlined",
    "personalized for you",
    "leaders like you",
    "people in your role",
    "I work with lots of",
    "open to chat",
    "open to a quick",
    "let me know if you'd like to",
    "would love to connect",
    # Surveillance / tracking clichés
    "noticed you visited",
    "saw you reading",
    "based on your interest",
    "when you were on our site",
    "intent signals",
    "based on your activity",
    "I saw that you",
]


# ============================================================================
# Approved Patterns
# ============================================================================

FIELD_NOTE_APPROVED_OPENERS: list[str] = [
    'Hi {first_name} —',
    'Hi {first_name} — quick note.',
    'Hi {first_name} — short field note for this week.',
]

FIELD_NOTE_APPROVED_CLOSERS: list[str] = [
    'No need to reply. Hope it helps.',
    'No reply needed. Hope it saves you time.',
    "That's it. Hope it helps.",
]

FIELD_NOTE_OPT_OUT_LINES: list[str] = [
    'If it\'s not useful, reply "stop" and I\'ll disappear.',
    'Reply "stop" any time and I\'ll stop sending these.',
    'If you don\'t want these, reply "stop" and I\'m gone.',
]


# ============================================================================
# Preferred Language — words/phrases that sound human and practical
# ============================================================================

FIELD_NOTE_PREFERRED_LANGUAGE: list[str] = [
    "quick test",
    "small move",
    "shows up as",
    "looks like X but it's actually Y",
    "the giveaway is",
    "if you only do one thing",
    "most teams do ___ first, but",
    "a simple pilot",
    "reduce noise",
    "late rework",
    "context is gone",
    "memory reconstruction",
    "bounded change",
    "one service line",
    "one workflow",
]


# ============================================================================
# Signal Classification — private vs public
# ============================================================================

# PRIVATE signals: use ONLY to choose topic, angle, examples, metrics
# NEVER reference in the email itself
PRIVATE_SIGNAL_FIELDS: list[str] = [
    "pages_visited",
    "content_category",
    "visit_count",
    "time_window",
    "inferred_pain_themes",
    "lead_score",
    "current_room",
    "engagement_signals",
    "urgency_signals",
    "urls_sent",
]

# PUBLIC context: safe to mention in the email
PUBLIC_CONTEXT_FIELDS: list[str] = [
    "company_name",
    "industry",
    "job_title",
    "contact_name",
    "employee_count",  # only as scale-aware wording, not exact numbers
    "location",
]


# ============================================================================
# Quality Checklist — each Field Note must pass all
# ============================================================================

FIELD_NOTE_QUALITY_CHECKLIST: list[str] = [
    "Contains one non-obvious quick test",
    "Contains at least two practical small moves",
    "Has one 'looks like X / actually Y' reframe",
    "Zero selling or pitching",
    "Value stands alone without clicking",
    "No mention of website visits or tracking",
    "No meeting requests or sales CTA",
    "Includes opt-out line",
    "Fits length standard (110-170 words)",
    "Reads like a useful peer note, not outreach",
]


# ============================================================================
# Subject Line Rules
# ============================================================================

FIELD_NOTE_SUBJECT_PREFIX: str = "Field Note:"

FIELD_NOTE_SUBJECT_BAN_WORDS: list[str] = [
    "free",
    "quick call",
    "resource",
    "checklist",
    "just checking",
    "following up",
    "limited time",
    "exclusive",
    "don't miss",
]
