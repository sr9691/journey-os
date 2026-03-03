# =============================================================================
# Guardrail Inspector Agent
# =============================================================================
#
# Validates generated content against room-specific guardrail rules
# from the RTR (Reading Room) methodology.
#
# Phase 4: Pattern-based inspection using pre-compiled regex from
# config/guardrails.py. Checks content against the rules for the
# prospect's current room (problem, solution, offer).
#
# Each room has different allowed language:
#   - Problem room: No company mentions, no pricing, no CTAs
#   - Solution room: Soft company references OK, no pricing/CTAs
#   - Offer room: Company mentions + pricing + CTAs OK, no aggressive sales
#   - All rooms: No superlatives, no competitor mentions
#
# The inspector runs AFTER content is ranked (and eventually after
# email generation in Phase 5) to validate the final output.
# =============================================================================

import logging
from typing import Any

from config.guardrails import (
    ViolationType,
    ROOM_RULES,
    find_pattern_matches,
    is_violation_checked,
    check_word_count,
)
from models.state import AgentState, GuardrailResult, GuardrailViolation

logger = logging.getLogger(__name__)

# Violation types that should block content (vs. warn)
BLOCKING_VIOLATIONS = {
    ViolationType.AGGRESSIVE_SALES,
    ViolationType.SUPERLATIVE,
    ViolationType.COMPETITOR_MENTION,
}

# Maximum violations before we flag for human review
MAX_VIOLATIONS_BEFORE_REVIEW = 3


async def inspect_guardrails(state: AgentState) -> dict[str, Any]:
    """Inspect content against room-specific guardrail rules.

    Reads: prospect_data (for current_room), selected_content, generated_email
    Returns: guardrail_result

    Currently inspects:
    - selected_content title (from asset ranker)
    - generated_email text (when available in Phase 5+)

    Future: Will also inspect email subject lines and CTA text.
    """

    prospect_data = state.get("prospect_data", {})
    room = prospect_data.get("current_room", "problem")
    prospect_id = state.get("prospect_id", 0)

    logger.info(
        "Inspecting guardrails",
        extra={"prospect_id": prospect_id, "room": room},
    )

    # Collect all text to inspect
    texts_to_check: list[str] = []

    # Check generated email if available (Phase 5+)
    generated_email = state.get("generated_email")
    if generated_email:
        texts_to_check.append(generated_email)

    # Check selected content title as a lightweight check
    selected = state.get("selected_content")
    if selected:
        texts_to_check.append(selected.title)

    # If no content to check, pass by default
    if not texts_to_check:
        logger.info(
            "No content to inspect, passing guardrails",
            extra={"prospect_id": prospect_id},
        )
        return {
            "guardrail_result": GuardrailResult(
                passed=True,
                room=room,
                checked_text="",
                suggestion="No content to inspect yet.",
            ),
            "current_step": "inspect_guardrails",
        }

    # Combine all text for inspection
    combined_text = "\n\n".join(texts_to_check)

    # Run all applicable checks for this room
    all_violations: list[GuardrailViolation] = []

    for violation_type in ViolationType:
        if not is_violation_checked(room, violation_type):
            continue

        matches = find_pattern_matches(combined_text, violation_type)

        for match_info in matches:
            severity = (
                "block" if violation_type in BLOCKING_VIOLATIONS else "warning"
            )

            all_violations.append(
                GuardrailViolation(
                    violation_type=violation_type.value,
                    matched_text=match_info["match"],
                    context=match_info.get("context", ""),
                    severity=severity,
                )
            )

    # --- Word count check (programmatic, not regex) ---
    if is_violation_checked(room, ViolationType.WORD_COUNT) and generated_email:
        # Extract body words (exclude Subject: line, greeting, signature, link line)
        body_word_count = _count_body_words(generated_email)
        wc_violations = check_word_count(body_word_count, room)
        for wc_match in wc_violations:
            all_violations.append(
                GuardrailViolation(
                    violation_type=ViolationType.WORD_COUNT.value,
                    matched_text=wc_match["match"],
                    context=wc_match.get("context", ""),
                    severity="warning",
                )
            )

    # --- Field Note subject prefix check (Problem Room only) ---
    if room == "problem" and generated_email:
        subject_line = _extract_subject(generated_email)
        if subject_line and not subject_line.startswith("Field Note:"):
            all_violations.append(
                GuardrailViolation(
                    violation_type="field_note_subject",
                    matched_text=subject_line[:60],
                    context="Problem Room emails must use 'Field Note:' subject prefix",
                    severity="warning",
                )
            )

    # Determine pass/fail
    has_blocking = any(v.severity == "block" for v in all_violations)
    passed = len(all_violations) == 0

    # Build human-readable suggestion
    suggestion = _build_suggestion(room, all_violations)

    result = GuardrailResult(
        passed=passed,
        room=room,
        violations=all_violations,
        violation_count=len(all_violations),
        checked_text=combined_text[:500],  # Truncate for state size
        suggestion=suggestion,
    )

    # Flag for human review if too many violations or blocking ones
    needs_review = (
        has_blocking
        or len(all_violations) >= MAX_VIOLATIONS_BEFORE_REVIEW
    )

    logger.info(
        "Guardrail inspection complete",
        extra={
            "prospect_id": prospect_id,
            "room": room,
            "passed": passed,
            "violation_count": len(all_violations),
            "has_blocking": has_blocking,
            "needs_review": needs_review,
        },
    )

    return {
        "guardrail_result": result,
        "requires_human_approval": needs_review,
        "current_step": "inspect_guardrails",
    }


# =============================================================================
# Standalone inspection (for testing or direct use)
# =============================================================================

def inspect_text(text: str, room: str) -> GuardrailResult:
    """Inspect arbitrary text against a room's guardrail rules.

    Useful for testing or for checking content outside the graph workflow.

    Args:
        text: The text to inspect.
        room: The RTR room to check against (problem, solution, offer).

    Returns:
        GuardrailResult with violations and pass/fail status.
    """

    all_violations: list[GuardrailViolation] = []

    for violation_type in ViolationType:
        if not is_violation_checked(room, violation_type):
            continue

        matches = find_pattern_matches(text, violation_type)

        for match_info in matches:
            severity = (
                "block" if violation_type in BLOCKING_VIOLATIONS else "warning"
            )
            all_violations.append(
                GuardrailViolation(
                    violation_type=violation_type.value,
                    matched_text=match_info["match"],
                    context=match_info.get("context", ""),
                    severity=severity,
                )
            )

    passed = len(all_violations) == 0
    suggestion = _build_suggestion(room, all_violations)

    # --- Word count check ---
    if is_violation_checked(room, ViolationType.WORD_COUNT):
        body_word_count = _count_body_words(text)
        wc_violations = check_word_count(body_word_count, room)
        for wc_match in wc_violations:
            all_violations.append(
                GuardrailViolation(
                    violation_type=ViolationType.WORD_COUNT.value,
                    matched_text=wc_match["match"],
                    context=wc_match.get("context", ""),
                    severity="warning",
                )
            )

    # --- Field Note subject prefix check (Problem Room only) ---
    if room == "problem":
        subject_line = _extract_subject(text)
        if subject_line and not subject_line.startswith("Field Note:"):
            all_violations.append(
                GuardrailViolation(
                    violation_type="field_note_subject",
                    matched_text=subject_line[:60],
                    context="Problem Room emails must use 'Field Note:' subject prefix",
                    severity="warning",
                )
            )

    passed = len(all_violations) == 0
    suggestion = _build_suggestion(room, all_violations)

    return GuardrailResult(
        passed=passed,
        room=room,
        violations=all_violations,
        violation_count=len(all_violations),
        checked_text=text[:500],
        suggestion=suggestion,
    )


# =============================================================================
# Helpers
# =============================================================================

def _build_suggestion(room: str, violations: list[GuardrailViolation]) -> str:
    """Build a human-readable suggestion from violations."""

    if not violations:
        return f"Content passes all {room} room guardrails."

    # Group by violation type
    by_type: dict[str, list[str]] = {}
    for v in violations:
        by_type.setdefault(v.violation_type, []).append(v.matched_text)

    parts = [f"Found {len(violations)} violation(s) for {room} room:"]

    type_labels = {
        "company_mention": "Remove company self-references",
        "pricing_language": "Remove pricing language",
        "sales_cta": "Remove sales call-to-action",
        "aggressive_sales": "Remove aggressive sales tactics",
        "superlative": "Remove superlative claims",
        "competitor_mention": "Remove competitor references",
        "unsupported_claim": "Add evidence for claims",
        "tone_mismatch": "Adjust tone for room",
        "word_count": "Adjust email length",
        "field_note_ban_list": "Remove banned outreach phrases",
        "signal_leakage": "Remove tracking/intent data references",
        "field_note_subject": "Add 'Field Note:' subject prefix",
    }

    for vtype, matches in by_type.items():
        label = type_labels.get(vtype, vtype)
        examples = ", ".join(f'"{m}"' for m in matches[:3])
        parts.append(f"  - {label}: {examples}")

    return "\n".join(parts)


def _count_body_words(email_text: str) -> int:
    # Count words in the email body, excluding subject line,
    # greeting (Hi X —), signature, and link line
    # Matches GPT spec: word count excludes greeting/signature/link

    lines = email_text.strip().split("\n")
    body_lines: list[str] = []
    skip_patterns = [
        "Subject:",
        "Hi ",
        "No need to reply",
        "Hope it helps",
        "[Sender Name]",
        "http://",
        "https://",
        "If you want the longer breakdown",
    ]

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) or p in stripped for p in skip_patterns):
            continue
        # Skip "I'm [Sender Name]." intro line
        if stripped.startswith("I'm ") and len(stripped) < 40:
            continue
        # Skip opt-out lines
        if "reply" in stripped.lower() and "stop" in stripped.lower():
            continue
        body_lines.append(stripped)

    body_text = " ".join(body_lines)
    return len(body_text.split())


def _extract_subject(email_text: str) -> str | None:
    # Extract subject line from email text
    # Looks for "Subject: ..." on first line

    lines = email_text.strip().split("\n")
    for line in lines[:3]:  # Check first 3 lines
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            return stripped[len("Subject:"):].strip()
    return None
