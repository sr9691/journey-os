# =============================================================================
# Revision Interpreter Agent
# =============================================================================
#
# Converts guardrail violations into actionable revision instructions
# that Gemini can use to regenerate a compliant email.
#
# This node sits between inspect_guardrails and compose_email in the
# revision loop. It reads the guardrail_result, builds specific edit
# instructions, and stores them in state for the email composer to use.
#
# Max 3 revision attempts before flagging for human approval.
# =============================================================================

import logging
import re
from typing import Any

from models.state import AgentState, GuardrailResult

logger = logging.getLogger(__name__)

# Maximum revision attempts before requiring human review
MAX_REVISION_ATTEMPTS = 3

# Maps violation types to specific revision instructions for Gemini
VIOLATION_INSTRUCTIONS: dict[str, str] = {
    "company_mention": (
        "Remove ALL self-referencing language. Do not use 'we', 'our', 'us' "
        "when referring to any company or service. Write from a neutral, "
        "third-party perspective."
    ),
    "company_name_leak": (
        "Remove the prospect's company name from the email entirely. "
        "Do NOT mention the recipient's company by name anywhere in the email. "
        "This is private data — use generic references like 'your team' or "
        "'organizations in your space' instead."
    ),
    "pricing_language": (
        "Remove all pricing, cost, or financial language. Do not mention "
        "prices, fees, ROI, return on investment, or any monetary references."
    ),
    "sales_cta": (
        "Remove all sales calls-to-action. Do not suggest booking demos, "
        "scheduling calls, or signing up for anything. The email should "
        "deliver value without asking for anything in return."
    ),
    "aggressive_sales": (
        "Remove aggressive sales tactics. No urgency language, no scarcity "
        "tactics, no pressure. The tone should be helpful and educational."
    ),
    "superlative": (
        "Remove ALL superlative claims from the EMAIL BODY. Do not use words "
        "like 'best', 'leading', 'top', '#1', 'premier', 'unmatched', "
        "'cutting-edge', 'world-class'. Use specific, factual language instead. "
        "Note: if 'best' appears only in the article title or link you are "
        "referencing, do not repeat it in your prose."
    ),
    "field_note_subject": (
        "The subject line MUST start with 'Field Note:' followed by a "
        "specific, lowercase observation. Fix the subject line."
    ),
    "field_note_ban_list": (
        "Remove banned outreach phrases. Do not use: 'reaching out', "
        "'touch base', 'quick call', '15 minutes', 'following up', "
        "'thought you might find this helpful', 'game-changing', "
        "'leaders like you'."
    ),
    "signal_leakage": (
        "Remove ALL references to tracking data, website visits, intent "
        "signals, or any indication that the recipient's behavior is being "
        "monitored. This is a hard privacy rule."
    ),
}

DEFAULT_INSTRUCTION = (
    "Fix the identified violation. Ensure the email complies with "
    "all room-specific guardrails."
)


def interpret_revisions(state: AgentState) -> dict[str, Any]:
    # Convert guardrail violations into revision instructions
    #
    # Reads: guardrail_result, revision_count, generated_email
    # Returns: revision_instructions (str), revision_count (incremented)

    guardrail_result = state.get("guardrail_result")
    revision_count = state.get("revision_count", 0)
    prospect_id = state.get("prospect_id", 0)

    if guardrail_result is None or guardrail_result.passed:
        logger.info(
            "No revisions needed — guardrails passed",
            extra={"prospect_id": prospect_id},
        )
        return {"current_step": "interpret_revisions"}

    new_count = revision_count + 1

    logger.info(
        "Interpreting revision instructions",
        extra={
            "prospect_id": prospect_id,
            "revision_attempt": new_count,
            "violation_count": guardrail_result.violation_count,
        },
    )

    instructions_parts: list[str] = []
    instructions_parts.append(
        f"## REVISION REQUIRED (attempt {new_count} of {MAX_REVISION_ATTEMPTS})\n"
    )
    instructions_parts.append(
        "The previous email draft had the following guardrail violations. "
        "Regenerate the email fixing ALL of these issues:\n"
    )

    # Deduplicate by violation type
    seen_types: set[str] = set()
    for violation in guardrail_result.violations:
        vtype = violation.violation_type
        if vtype in seen_types:
            continue
        seen_types.add(vtype)

        # For word_count, build a concrete instruction from the actual count
        if vtype == "word_count":
            instruction = _build_word_count_instruction(
                violation.matched_text, state
            )
        else:
            instruction = VIOLATION_INSTRUCTIONS.get(vtype, DEFAULT_INSTRUCTION)

        matched = violation.matched_text
        instructions_parts.append(
            f"- **{vtype}**: Found '{matched}'. {instruction}"
        )

    instructions_parts.append(
        "\nGenerate a COMPLETE new email that fixes all violations above "
        "while preserving the original intent, structure, and content link."
    )

    revision_instructions = "\n".join(instructions_parts)

    logger.info(
        "Revision instructions built",
        extra={
            "prospect_id": prospect_id,
            "revision_attempt": new_count,
            "violation_types": list(seen_types),
        },
    )

    return {
        "revision_instructions": revision_instructions,
        "revision_count": new_count,
        "current_step": "interpret_revisions",
    }


def _build_word_count_instruction(matched_text: str, state: AgentState) -> str:
    # Build a concrete word count instruction from the violation match text.
    # matched_text is e.g. "Word count: 98 (min: 110)" or "Word count: 185 (max: 170)"
    # Extract the actual count and give Gemini a specific target.

    prospect_data = state.get("prospect_data", {})
    room = prospect_data.get("current_room", "problem")

    # Parse current word count from matched_text
    current_count = 0
    count_match = re.search(r"Word count: (\d+)", matched_text)
    if count_match:
        current_count = int(count_match.group(1))

    # Room-specific targets
    targets = {
        "problem": (110, 150, 130),
        "solution": (150, 350, 250),
        "offer": (150, 400, 275),
    }
    min_wc, max_wc, target_wc = targets.get(room, (110, 170, 130))

    if current_count < min_wc:
        delta = min_wc - current_count
        return (
            f"The email body is currently {current_count} words, which is below "
            f"the minimum of {min_wc}. Add approximately {delta} more words by "
            f"expanding one observation with a specific detail or consequence. "
            f"Target {target_wc} words total in the body "
            f"(excluding greeting, signature, and link line)."
        )
    else:
        delta = current_count - max_wc
        return (
            f"The email body is currently {current_count} words, which exceeds "
            f"the maximum of {max_wc}. Remove approximately {delta} words by "
            f"trimming adjectives and redundant clauses. "
            f"Target {target_wc} words total in the body "
            f"(excluding greeting, signature, and link line)."
        )
