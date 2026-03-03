# config/guardrails.py
# Room-specific guardrails for content validation
# Updated: Added word count, Field Note ban list, and signal leakage checks

from __future__ import annotations

import re
import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Room Thresholds (RTR methodology)
# ============================================================================

ROOM_THRESHOLDS: dict[str, int] = {
    "problem_max": 40,
    "solution_max": 60,
    "offer_min": 61,
}


# ============================================================================
# Violation Types
# ============================================================================

class ViolationType(str, Enum):
    COMPANY_MENTION = "company_mention"
    SOLUTION_MENTION = "solution_mention"
    PRICING_LANGUAGE = "pricing_language"
    SALES_CTA = "sales_cta"
    AGGRESSIVE_SALES = "aggressive_sales"
    SUPERLATIVE = "superlative"
    COMPETITOR_MENTION = "competitor_mention"
    WORD_COUNT = "word_count"
    FIELD_NOTE_BAN_LIST = "field_note_ban_list"
    SIGNAL_LEAKAGE = "signal_leakage"


# ============================================================================
# Pattern Definitions
# ============================================================================

COMPANY_MENTION_PATTERNS: list[str] = [
    r"\bwe\b(?:\s+(?:offer|provide|deliver|help|specialize|build|create))",
    r"\bour\b(?:\s+(?:solution|platform|service|product|team|approach|offering))",
    r"\bus\b(?:\s+(?:to|for|about))",
]

SOLUTION_MENTION_PATTERNS: list[str] = [
    r"\b(?:our|the)\s+(?:platform|software|tool|solution|product|service)\b",
    r"\bproprietary\b",
    r"\bfeature[sd]?\b(?:\s+(?:include|like|such))",
]

PRICING_LANGUAGE_PATTERNS: list[str] = [
    r"\$\d+",
    r"\b(?:pricing|price|fee|rate|subscription|plan|tier)\b",
    r"\b(?:discount|offer|deal|savings|free trial)\b",
    r"\bcost\s+(?:of|per|for|to)\s+(?:the\s+)?(?:service|platform|product|license|tool)\b",
    r"\bROI\b",
    r"\breturn on investment\b",
]

SALES_CTA_PATTERNS: list[str] = [
    r"\b(?:book|schedule|request)\s+(?:a\s+)?(?:demo|call|meeting|consultation)\b",
    r"\b(?:sign up|register|subscribe)\s+(?:now|today|here|for|to)\b",
    r"\b(?:get started|start your|try it|buy now|order now)\b",
    r"\b(?:contact us|reach out to us|talk to (?:us|our|a rep))\b",
    r"\b(?:free trial|free consultation)\b",
]

AGGRESSIVE_SALES_PATTERNS: list[str] = [
    r"\b(?:limited time|act now|don't miss|hurry|expires?|last chance)\b",
    r"\b(?:exclusive|only \d+ (?:left|remaining|spots?))\b",
    r"\b(?:risk.free|no.risk|guaranteed|100%)\b",
    r"\b(?:before it's too late|while (?:supplies|stocks?) last)\b",
]

SUPERLATIVE_PATTERNS: list[str] = [
    r"\b(?:leading|premier|world.class|cutting.edge)\b",
    r"\b(?:industry.leading|market.leading|best.in.class)\b",
    r"\bbest\b(?!\s+\d)",  # "best" but not "best 3" etc.
    r"\btop\b(?!\s+\d)(?:\s+(?:rated|performing|tier|choice|pick|notch))",  # "top rated" but not "top 3"
    r"#\s*1\b",
    r"\bnumber\s+one\b",
    r"\b(?:unmatched|unparalleled|unrivaled|unbeatable)\b",
]

COMPETITOR_PATTERNS: list[str] = [
    # Intentionally empty — populated per-client via SourceBundle
    # Add competitor names as needed
]

# Signal leakage patterns — detect when email mentions tracking/intent data
SIGNAL_LEAKAGE_PATTERNS: list[str] = [
    r"\b(?:noticed|saw|observed)\s+(?:you|your)\s+(?:visit|read|view|click|download)",
    r"\b(?:based on|given)\s+(?:your|the)\s+(?:interest|activity|engagement|visit)",
    r"\b(?:when you|after you)\s+(?:visited|read|viewed|clicked|downloaded)",
    r"\b(?:your recent|your latest)\s+(?:visit|activity|engagement|search)",
    r"\b(?:intent\s+(?:signal|data))\b",
    r"\b(?:tracking|tracked|we track)\b",
    r"\b(?:on our site|on our website|on the website)\b",
    r"\b(?:browsing|browse history|page views?)\b",
    r"\b(?:based on what you|based on your browsing)\b",
]

# Field Note ban list patterns — compile from the spec
FIELD_NOTE_BAN_PATTERNS: list[str] = [
    r"\b(?:i'm reaching out|reaching out)\b",
    r"\b(?:touch base|circle back)\b",
    r"\b(?:quick call|hop on a call)\b",
    r"\b15 minutes\b",
    r"\b(?:are you available|would you be available)\b",
    r"\b(?:following up|just checking in)\b",
    r"\bthought you might find this helpful\b",
    r"\b(?:high.value|game.changing|game changer)\b",
    r"\b(?:unlock|leverage|synergy|streamlined)\b",
    r"\b(?:personalized for you)\b",
    r"\b(?:leaders like you|people in your role)\b",
    r"\b(?:I work with lots of|I work with many)\b",
    r"\b(?:open to (?:chat|a quick|connecting))\b",
    r"\b(?:would love to connect)\b",
    r"\b(?:let me know if you'd like to)\b",
]


# ============================================================================
# Pattern Compilation
# ============================================================================

def _compile_patterns(patterns: list[str]) -> re.Pattern | None:
    # Compile a list of regex patterns into a single combined pattern
    if not patterns:
        return None
    combined = "|".join(f"(?:{p})" for p in patterns)
    return re.compile(combined, re.IGNORECASE)


COMPILED_PATTERNS: dict[ViolationType, re.Pattern | None] = {
    ViolationType.COMPANY_MENTION: _compile_patterns(COMPANY_MENTION_PATTERNS),
    ViolationType.SOLUTION_MENTION: _compile_patterns(SOLUTION_MENTION_PATTERNS),
    ViolationType.PRICING_LANGUAGE: _compile_patterns(PRICING_LANGUAGE_PATTERNS),
    ViolationType.SALES_CTA: _compile_patterns(SALES_CTA_PATTERNS),
    ViolationType.AGGRESSIVE_SALES: _compile_patterns(AGGRESSIVE_SALES_PATTERNS),
    ViolationType.SUPERLATIVE: _compile_patterns(SUPERLATIVE_PATTERNS),
    ViolationType.COMPETITOR_MENTION: _compile_patterns(COMPETITOR_PATTERNS),
    ViolationType.SIGNAL_LEAKAGE: _compile_patterns(SIGNAL_LEAKAGE_PATTERNS),
    ViolationType.FIELD_NOTE_BAN_LIST: _compile_patterns(FIELD_NOTE_BAN_PATTERNS),
    # WORD_COUNT is checked programmatically, not via regex
    ViolationType.WORD_COUNT: None,
}


# ============================================================================
# Room Rules — which violations to check per room
# ============================================================================

ROOM_RULES: dict[str, dict[ViolationType, bool]] = {
    "problem": {
        ViolationType.COMPANY_MENTION: True,
        ViolationType.SOLUTION_MENTION: True,
        ViolationType.PRICING_LANGUAGE: True,
        ViolationType.SALES_CTA: True,
        ViolationType.AGGRESSIVE_SALES: True,
        ViolationType.SUPERLATIVE: True,
        ViolationType.COMPETITOR_MENTION: True,
        ViolationType.WORD_COUNT: True,
        ViolationType.FIELD_NOTE_BAN_LIST: True,
        ViolationType.SIGNAL_LEAKAGE: True,
    },
    "solution": {
        ViolationType.COMPANY_MENTION: False,  # Soft mentions OK
        ViolationType.SOLUTION_MENTION: False,  # Educational refs OK
        ViolationType.PRICING_LANGUAGE: True,
        ViolationType.SALES_CTA: True,
        ViolationType.AGGRESSIVE_SALES: True,
        ViolationType.SUPERLATIVE: True,
        ViolationType.COMPETITOR_MENTION: True,
        ViolationType.WORD_COUNT: True,
        ViolationType.FIELD_NOTE_BAN_LIST: False,  # Only for Field Notes
        ViolationType.SIGNAL_LEAKAGE: True,
    },
    "offer": {
        ViolationType.COMPANY_MENTION: False,
        ViolationType.SOLUTION_MENTION: False,
        ViolationType.PRICING_LANGUAGE: False,
        ViolationType.SALES_CTA: False,
        ViolationType.AGGRESSIVE_SALES: True,  # Always check
        ViolationType.SUPERLATIVE: True,         # Always check
        ViolationType.COMPETITOR_MENTION: True,  # Always check
        ViolationType.WORD_COUNT: True,
        ViolationType.FIELD_NOTE_BAN_LIST: False,
        ViolationType.SIGNAL_LEAKAGE: True,
    },
}


# ============================================================================
# Word Count Limits per Room
# ============================================================================

WORD_COUNT_LIMITS: dict[str, dict[str, int]] = {
    "problem": {
        "min": 110,
        "max": 170,
        "target": 130,
    },
    "solution": {
        "min": 150,
        "max": 350,
        "target": 250,
    },
    "offer": {
        "min": 150,
        "max": 400,
        "target": 275,
    },
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_room_from_score(lead_score: int) -> str:
    # Determine room based on lead score
    if lead_score <= ROOM_THRESHOLDS["problem_max"]:
        return "problem"
    elif lead_score <= ROOM_THRESHOLDS["solution_max"]:
        return "solution"
    else:
        return "offer"


def is_violation_checked(room: str, violation_type: ViolationType) -> bool:
    # Check if a violation type should be checked for a given room
    room_lower = room.lower()
    if room_lower not in ROOM_RULES:
        # Default to most restrictive (problem room) if unknown
        room_lower = "problem"
    return ROOM_RULES[room_lower].get(violation_type, True)


def find_pattern_matches(
    text: str,
    violation_type: ViolationType,
) -> list[dict[str, Any]]:
    # Find all matches of a violation pattern in text
    # Returns list of dicts with 'match', 'start', 'end' keys

    pattern = COMPILED_PATTERNS.get(violation_type)
    if not pattern:
        return []

    matches = []
    for match in pattern.finditer(text):
        matches.append({
            "match": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "context": _get_context(text, match.start(), match.end()),
        })

    return matches


def check_word_count(
    body_word_count: int,
    room: str,
) -> list[dict[str, Any]]:
    # Check if word count is within limits for the room
    # Returns list of violation dicts (empty if count is OK)

    room_lower = room.lower()
    limits = WORD_COUNT_LIMITS.get(room_lower)
    if not limits:
        return []

    violations = []

    if body_word_count > limits["max"]:
        violations.append({
            "match": f"Word count: {body_word_count} (max: {limits['max']})",
            "start": 0,
            "end": 0,
            "context": (
                f"Email body is {body_word_count} words. "
                f"Target: {limits['target']}, Max: {limits['max']}. "
                f"Trim by removing adjectives and clauses that don't change meaning."
            ),
        })
    elif body_word_count < limits["min"]:
        violations.append({
            "match": f"Word count: {body_word_count} (min: {limits['min']})",
            "start": 0,
            "end": 0,
            "context": (
                f"Email body is {body_word_count} words. "
                f"Target: {limits['target']}, Min: {limits['min']}. "
                f"Add more specific detail or an additional small move."
            ),
        })

    return violations


def _get_context(text: str, start: int, end: int, window: int = 50) -> str:
    # Extract surrounding context for a match
    context_start = max(0, start - window)
    context_end = min(len(text), end + window)
    context = text[context_start:context_end]
    if context_start > 0:
        context = "..." + context
    if context_end < len(text):
        context = context + "..."
    return context
