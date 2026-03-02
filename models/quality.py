# models/quality.py
# Quality control models for guardrail inspection
# Updated: Added WORD_COUNT, FIELD_NOTE_BAN_LIST, and SIGNAL_LEAKAGE violation types

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Violation Types
# ============================================================================

class ViolationSeverity(str, Enum):
    # How serious is the violation
    CRITICAL = "critical"    # Must fix before sending
    WARNING = "warning"      # Should review, may be acceptable
    INFO = "info"            # Informational, no action required


class ViolationType(str, Enum):
    # Types of content violations
    COMPANY_MENTION = "company_mention"
    SOLUTION_MENTION = "solution_mention"
    PRICING_LANGUAGE = "pricing_language"
    SALES_CTA = "sales_cta"
    AGGRESSIVE_SALES = "aggressive_sales"
    SUPERLATIVE = "superlative"
    COMPETITOR_MENTION = "competitor_mention"
    # New violation types
    WORD_COUNT = "word_count"
    FIELD_NOTE_BAN_LIST = "field_note_ban_list"
    SIGNAL_LEAKAGE = "signal_leakage"


# ============================================================================
# Violation Model
# ============================================================================

class Violation(BaseModel):
    # A single content violation found during inspection

    violation_type: ViolationType = Field(
        ..., description="Type of violation"
    )
    severity: ViolationSeverity = Field(
        ..., description="Severity level"
    )
    match_text: str = Field(
        default="", description="The text that triggered the violation"
    )
    context: str = Field(
        default="", description="Surrounding text for context"
    )
    explanation: str = Field(
        default="", description="Why this is a violation"
    )
    suggested_fix: str = Field(
        default="", description="How to fix this violation"
    )
    position: int = Field(
        default=-1, description="Character position in text"
    )


# ============================================================================
# Content To Inspect
# ============================================================================

class ContentToInspect(BaseModel):
    # Content submitted for guardrail inspection

    subject: str = Field(default="", description="Email subject line")
    body: str = Field(default="", description="Email body text")
    sender_name: str = Field(default="", description="Sender name")

    def get_full_text(self) -> str:
        # Combine subject and body for full text inspection
        parts = []
        if self.subject:
            parts.append(self.subject)
        if self.body:
            parts.append(self.body)
        return "\n".join(parts)

    def get_body_word_count(self) -> int:
        # Count words in the body, excluding greeting and signature lines
        # This strips the greeting (Hi X —), sender intro, opt-out line,
        # link line, and closing

        if not self.body:
            return 0

        lines = self.body.strip().split("\n")
        content_lines = []
        skip_patterns = [
            "hi ",          # greeting
            "i'm ",         # sender intro
            "i send one",   # cadence line
            "if it's not",  # opt-out
            "reply \"stop", # opt-out variant
            "if you don't", # opt-out variant
            "no need to reply",  # closer
            "no reply needed",   # closer variant
            "that's it.",        # closer variant
            "http",              # link line
            "here it is",       # link line
        ]

        for line in lines:
            line_lower = line.strip().lower()
            if not line_lower:
                continue
            # Skip if the line matches any skip pattern
            if any(line_lower.startswith(p) for p in skip_patterns):
                continue
            # Skip if it's just the sender name (short line, no spaces)
            if len(line.strip().split()) <= 2 and not any(
                c in line for c in [":", "—", "-", "."]
            ):
                # Likely just a name
                if line.strip() == self.sender_name:
                    continue
            content_lines.append(line.strip())

        text = " ".join(content_lines)
        return len(text.split())


# ============================================================================
# Guardrail Result
# ============================================================================

class GuardrailResult(BaseModel):
    # Result of guardrail inspection

    status: str = Field(
        ..., description="pass or fail"
    )
    room: str = Field(
        default="", description="Room the content was inspected for"
    )
    violations: list[Violation] = Field(
        default_factory=list, description="List of violations found"
    )
    checked_rules: list[str] = Field(
        default_factory=list, description="Rules that were checked"
    )
    content_length: int = Field(
        default=0, description="Length of inspected content"
    )
    body_word_count: int = Field(
        default=0, description="Word count of body (excluding greeting/sig)"
    )

    @classmethod
    def create_pass(
        cls,
        room: str,
        checked_rules: list[str],
        content_length: int = 0,
        body_word_count: int = 0,
    ) -> GuardrailResult:
        return cls(
            status="pass",
            room=room,
            violations=[],
            checked_rules=checked_rules,
            content_length=content_length,
            body_word_count=body_word_count,
        )

    @classmethod
    def create_fail(
        cls,
        room: str,
        violations: list[Violation],
        checked_rules: list[str],
        content_length: int = 0,
        body_word_count: int = 0,
    ) -> GuardrailResult:
        return cls(
            status="fail",
            room=room,
            violations=violations,
            checked_rules=checked_rules,
            content_length=content_length,
            body_word_count=body_word_count,
        )

    @property
    def critical_count(self) -> int:
        return sum(
            1 for v in self.violations
            if v.severity == ViolationSeverity.CRITICAL
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for v in self.violations
            if v.severity == ViolationSeverity.WARNING
        )


# ============================================================================
# Violation Explanations (per type per room)
# ============================================================================

VIOLATION_EXPLANATIONS: dict[ViolationType, dict[str, str]] = {
    ViolationType.COMPANY_MENTION: {
        "problem": "Problem Room emails must not mention the sending company.",
        "solution": "Solution Room allows soft company references only.",
        "offer": "Offer Room allows company mentions.",
    },
    ViolationType.SOLUTION_MENTION: {
        "problem": "Problem Room must focus on the problem, not solutions.",
        "solution": "Solution Room should educate about approaches, not hard-sell.",
        "offer": "Offer Room allows solution discussions.",
    },
    ViolationType.PRICING_LANGUAGE: {
        "problem": "Problem Room must not contain pricing references.",
        "solution": "Solution Room must not contain pricing references.",
        "offer": "Offer Room allows pricing discussions.",
    },
    ViolationType.SALES_CTA: {
        "problem": "Problem Room must not contain sales calls-to-action.",
        "solution": "Solution Room should use soft CTAs only.",
        "offer": "Offer Room allows direct CTAs.",
    },
    ViolationType.AGGRESSIVE_SALES: {
        "problem": "No urgency or scarcity tactics allowed.",
        "solution": "No urgency or scarcity tactics allowed.",
        "offer": "Even Offer Room should avoid aggressive tactics.",
    },
    ViolationType.SUPERLATIVE: {
        "problem": "Superlatives are banned in all rooms.",
        "solution": "Superlatives are banned in all rooms.",
        "offer": "Superlatives are banned in all rooms.",
    },
    ViolationType.COMPETITOR_MENTION: {
        "problem": "Competitor mentions are banned in all rooms.",
        "solution": "Competitor mentions are banned in all rooms.",
        "offer": "Competitor mentions are banned in all rooms.",
    },
    ViolationType.WORD_COUNT: {
        "problem": "Field Note emails must be 110-170 words (body only).",
        "solution": "Email body should be 200-300 words.",
        "offer": "Email body should be 200-350 words.",
    },
    ViolationType.FIELD_NOTE_BAN_LIST: {
        "problem": "This phrase is on the Field Note ban list.",
        "solution": "This phrase sounds like sales outreach.",
        "offer": "This phrase sounds like generic outreach.",
    },
    ViolationType.SIGNAL_LEAKAGE: {
        "problem": "Email must not reference website visits, tracking, or intent signals.",
        "solution": "Email must not reference website visits, tracking, or intent signals.",
        "offer": "Email must not reference website visits, tracking, or intent signals.",
    },
}


# ============================================================================
# Suggested Fixes (per violation type)
# ============================================================================

SUGGESTED_FIXES: dict[ViolationType, str] = {
    ViolationType.COMPANY_MENTION: (
        "Remove company name. Rewrite from the prospect's perspective."
    ),
    ViolationType.SOLUTION_MENTION: (
        "Remove solution/product references. Focus on the problem."
    ),
    ViolationType.PRICING_LANGUAGE: (
        "Remove pricing references. Focus on value and outcomes."
    ),
    ViolationType.SALES_CTA: (
        "Replace sales CTA with educational action "
        "(e.g., 'learn more', 'explore the guide')."
    ),
    ViolationType.AGGRESSIVE_SALES: (
        "Remove urgency language. Let the content speak for itself."
    ),
    ViolationType.SUPERLATIVE: (
        "Replace with factual statement or remove entirely."
    ),
    ViolationType.COMPETITOR_MENTION: (
        "Remove competitor reference. Focus on your approach."
    ),
    ViolationType.WORD_COUNT: (
        "Trim the email body. Remove adjectives and clauses that don't "
        "change meaning. Prefer deleting over rephrasing."
    ),
    ViolationType.FIELD_NOTE_BAN_LIST: (
        "Remove or rewrite this phrase. It sounds like sales outreach, "
        "not a helpful peer note."
    ),
    ViolationType.SIGNAL_LEAKAGE: (
        "Remove any reference to website visits, pages viewed, tracking, "
        "or how you found the prospect. Use private signals only for "
        "topic selection, never mention them in the email."
    ),
}
