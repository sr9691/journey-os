# config/guardrails.py
# Room-specific guardrail rules for RTR methodology
# Agent #25 (Guardrail Inspector) uses these rules to validate content

from __future__ import annotations
import re
from enum import Enum
from typing import Any

# -----------------------------------------------------------------------------
# Room Thresholds
# -----------------------------------------------------------------------------

ROOM_THRESHOLDS = {
    "problem_max": 40,
    "solution_max": 60,
    "offer_min": 61,
}


# -----------------------------------------------------------------------------
# Pattern Definitions
# -----------------------------------------------------------------------------

# Patterns that indicate company/product self-reference
COMPANY_PATTERNS = [
    r"\bwe\b(?:\s+(?:can|will|offer|provide|help|specialize|deliver))",
    r"\bour\b\s+(?:team|solution|service|platform|approach|experts?)",
    r"\bwe[\u2019']re\b",
    r"\bour\s+company\b",
    r"\bus\b\s+(?:today|now|for)",
]

# Pricing-related patterns
# These are designed to catch pricing discussions, not general problem descriptions
PRICING_PATTERNS = [
    r"\$\d+",                                          # Dollar amounts
    r"\bpric(?:e|ing|ed)\b",                          # Price/pricing
    r"\b(?:our|the)\s+cost(?:s)?\s+(?:start|begin|are)\b",  # "our costs start at..."
    r"\bcost\s+of\s+\$?\d+\b",                        # "cost of $X"
    r"\bfee(?:s)?\s+(?:start|begin|of|are)\b",       # "fees start at..."
    r"\bquote\s+(?:for|of)\b",                       # "quote for/of"
    r"\bget\s+a\s+quote\b",                          # "get a quote"
    r"\binvestment\s+(?:of|starting)\b",             # "investment of/starting"
    r"\bROI\b",                                       # ROI
    r"\breturn\s+on\s+investment\b",                 # Return on investment
    r"\bsave\s+(?:up\s+to\s+)?\d+%",                 # "save X%"
    r"\bpay(?:ment)?s?\s+(?:of|starting)\s+\$?\d+",  # "payments of $X"
]

# Demo/sales CTA patterns
SALES_CTA_PATTERNS = [
    r"\bbook\s+(?:a\s+)?(?:demo|call|meeting|consultation)\b",
    r"\bschedule\s+(?:a\s+)?(?:demo|call|meeting|consultation)\b",
    r"\brequest\s+(?:a\s+)?(?:demo|quote|pricing)\b",
    r"\bget\s+started\s+(?:today|now)\b",
    r"\bcontact\s+(?:us|our\s+team|sales)\b",
    r"\bspeak\s+(?:to|with)\s+(?:an?\s+)?(?:expert|specialist|consultant)\b",
    r"\bfree\s+(?:trial|consultation|assessment)\b",
    r"\bsign\s+up\b",
    r"\btry\s+(?:it\s+)?(?:free|now|today)\b",
]

# Aggressive sales language patterns
AGGRESSIVE_SALES_PATTERNS = [
    r"\bdon[\u2019']t\s+miss\b",
    r"\bact\s+(?:now|fast|today)\b",
    r"\blimited\s+(?:time|offer|availability)\b",
    r"\bexclusive\s+(?:offer|deal|discount)\b",
    r"\bhurry\b",
    r"\burgent\b",
    r"\blast\s+chance\b",
    r"\bonly\s+\d+\s+(?:spots?|seats?)\s+(?:left|remaining)\b",
    r"\bwhile\s+(?:supplies|stocks?)\s+last\b",
]

# Superlative patterns (universal violation)
# Avoid matching numbered lists (1., 2., etc.)
SUPERLATIVE_PATTERNS = [
    r"\b(?:the\s+)?best\b",
    r"\b(?:the\s+)?leading\b",
    r"\b#\s*1\b",                         # #1 but not plain numbers
    r"\bnumber\s+one\b",
    r"\btop[-\s]?(?:rated|ranked|tier)\b",
    r"\bworld[-\s]?class\b",
    r"\bindustry[-\s]?leading\b",
    r"\bunmatched\b",
    r"\bunparalleled\b",
    r"\bguaranteed\b",
]

# Competitor mention patterns (will be expanded with actual names)
# Base patterns that suggest competitor comparison
COMPETITOR_PATTERNS = [
    r"\bunlike\s+(?:other|competing)\b",
    r"\bcompared\s+to\s+\w+\b",
    r"\bbetter\s+than\s+\w+\b",
    r"\bswitch\s+from\s+\w+\b",
]


# -----------------------------------------------------------------------------
# Violation Types
# -----------------------------------------------------------------------------

class ViolationType(str, Enum):
    # Content contains prohibited self-reference for the room
    COMPANY_MENTION = "company_mention"
    # Content contains pricing language inappropriate for the room
    PRICING_LANGUAGE = "pricing_language"
    # Content contains sales CTA inappropriate for the room
    SALES_CTA = "sales_cta"
    # Content uses aggressive sales tactics
    AGGRESSIVE_SALES = "aggressive_sales"
    # Content uses superlatives (universal violation)
    SUPERLATIVE = "superlative"
    # Content mentions competitors by name
    COMPETITOR_MENTION = "competitor_mention"
    # Content makes unsupported claims
    UNSUPPORTED_CLAIM = "unsupported_claim"
    # Content tone is inappropriate for the room
    TONE_MISMATCH = "tone_mismatch"


# -----------------------------------------------------------------------------
# Room-Specific Rules
# -----------------------------------------------------------------------------

# Maps room name to which violation types are checked
# True = violation is checked, False = allowed in this room
ROOM_RULES: dict[str, dict[ViolationType, bool]] = {
    "problem": {
        ViolationType.COMPANY_MENTION: True,     # No "we/our" language
        ViolationType.PRICING_LANGUAGE: True,    # No pricing
        ViolationType.SALES_CTA: True,           # No sales CTAs
        ViolationType.AGGRESSIVE_SALES: True,    # No aggressive sales
        ViolationType.SUPERLATIVE: True,         # No superlatives (universal)
        ViolationType.COMPETITOR_MENTION: True,  # No competitor names (universal)
    },
    "solution": {
        ViolationType.COMPANY_MENTION: False,    # Soft references OK
        ViolationType.PRICING_LANGUAGE: True,    # No pricing
        ViolationType.SALES_CTA: True,           # No aggressive CTAs
        ViolationType.AGGRESSIVE_SALES: True,    # No aggressive sales
        ViolationType.SUPERLATIVE: True,         # No superlatives (universal)
        ViolationType.COMPETITOR_MENTION: True,  # No competitor names (universal)
    },
    "offer": {
        ViolationType.COMPANY_MENTION: False,    # May mention client offerings
        ViolationType.PRICING_LANGUAGE: False,   # May include pricing
        ViolationType.SALES_CTA: False,          # May include demo CTAs
        ViolationType.AGGRESSIVE_SALES: True,    # Still no aggressive tactics
        ViolationType.SUPERLATIVE: True,         # No superlatives (universal)
        ViolationType.COMPETITOR_MENTION: True,  # No competitor names (universal)
    },
}


# -----------------------------------------------------------------------------
# Pattern Compilation
# -----------------------------------------------------------------------------

def _compile_patterns(patterns: list[str]) -> re.Pattern[str]:
    # Compile a list of patterns into a single regex
    combined = "|".join(f"({p})" for p in patterns)
    return re.compile(combined, re.IGNORECASE)


# Pre-compiled pattern matchers for performance
COMPILED_PATTERNS: dict[ViolationType, re.Pattern[str]] = {
    ViolationType.COMPANY_MENTION: _compile_patterns(COMPANY_PATTERNS),
    ViolationType.PRICING_LANGUAGE: _compile_patterns(PRICING_PATTERNS),
    ViolationType.SALES_CTA: _compile_patterns(SALES_CTA_PATTERNS),
    ViolationType.AGGRESSIVE_SALES: _compile_patterns(AGGRESSIVE_SALES_PATTERNS),
    ViolationType.SUPERLATIVE: _compile_patterns(SUPERLATIVE_PATTERNS),
    ViolationType.COMPETITOR_MENTION: _compile_patterns(COMPETITOR_PATTERNS),
}


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

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


def _get_context(text: str, start: int, end: int, window: int = 50) -> str:
    # Get surrounding context for a match
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    
    prefix = "..." if ctx_start > 0 else ""
    suffix = "..." if ctx_end < len(text) else ""
    
    return f"{prefix}{text[ctx_start:ctx_end]}{suffix}"