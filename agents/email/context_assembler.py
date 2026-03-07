# agents/email/context_assembler.py
# Email Context Assembler Agent (#18)
# Creates complete Gemini API payload for email generation
# Updated: max_tokens=16384, signal firewall, insight integration

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime

from models.state import AgentState
from models.prospect import ContentAsset
from models.prospect import ProspectIntent, Room
from agents.email.prompt_template_builder import (
    assemble_full_prompt,
    EMAIL_FORMAT_FIELD_NOTE,
    EMAIL_FORMAT_STANDARD,
    SIGNAL_FIREWALL_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Gemini API Configuration
# ============================================================================

# Default max_output_tokens set to 16384 for all requests
DEFAULT_GENERATION_CONFIG: dict[str, Any] = {
    "model": "gemini-2.0-flash",
    "temperature": 0.7,
    "max_output_tokens": 16384,
    "top_p": 0.9,
    "top_k": 40,
}

# Room-specific generation adjustments
ROOM_GENERATION_OVERRIDES: dict[Room, dict[str, Any]] = {
    Room.PROBLEM: {
        "temperature": 0.6,  # More conservative for educational tone
    },
    Room.SOLUTION: {
        "temperature": 0.7,  # Balanced creativity
    },
    Room.OFFER: {
        "temperature": 0.5,  # More precise for offers
    },
}


# ============================================================================
# System Instructions
# ============================================================================

GEMINI_SYSTEM_INSTRUCTION = """You are an expert B2B email copywriter specializing in nurture campaigns.

Your writing style:
- Plainspoken, direct, human
- Short sentences, easy to scan
- No hype, no buzzwords, no flattery
- Specific tests and actions over vague advice
- One idea per sentence

Output Requirements:
- Generate valid JSON with "subject" and "body" keys
- The "body" should be plain text (not HTML)
- Follow ALL room-specific guardrails exactly
- Follow ALL length constraints exactly
- PLAIN TEXT ONLY in the body — no markdown bold (**text**), italics (*text**),
  headers (##), or [text](url) link syntax. Write URLs as raw text.

{signal_firewall}
"""

GEMINI_FIELD_NOTE_SYSTEM = """You are an expert at writing short, practical "Field Note" emails for B2B prospects.

These are NOT cold sales emails. They are short weekly notes that deliver real value inside the email.

Your writing style:
- Plainspoken, direct, like a smart colleague sharing a practical observation
- Short sentences. Simple words. One idea per sentence.
- No hype, no buzzwords, no flattery, no outreach clichés
- Every claim must be grounded in the article content provided
- If the recipient forwarded this email internally, it should still read like a useful note

Output Requirements:
- Generate valid JSON with "subject" and "body" keys
- Subject MUST start with "Field Note:"
- Body must be plain text — absolutely no markdown formatting
- Body must be 110-170 words (excluding greeting/signature/link)
- Follow the exact structure: What's happening → The real cause → Quick test → What to do next
- Section headers must be plain text labels (e.g. "What's happening:") — no asterisks or bold markers

Banned phrases (NEVER use):
- "I'm reaching out" / "reaching out" / "touch base" / "circle back"
- "quick call" / "15 minutes" / "hop on a call"
- "following up" / "just checking in"
- "thought you might find this helpful"
- "game-changing" / "unlock" / "leverage" / "synergy"
- "leaders like you" / "personalized for you"
- Any reference to website visits, tracking, or intent data

Banned formatting (NEVER use):
- Markdown bold: **text**
- Markdown italics: *text*
- Markdown headers: ## Heading
- Markdown link syntax: [link text](https://url.com) — write the raw URL instead
- Any other markdown or HTML formatting

{signal_firewall}
"""


# ============================================================================
# Helper Functions
# ============================================================================

def _get_system_instruction(
    room: Room,
    email_format: str = EMAIL_FORMAT_FIELD_NOTE,
) -> str:
    # Get room-appropriate system instruction for Gemini

    if room == Room.PROBLEM and email_format == EMAIL_FORMAT_FIELD_NOTE:
        return GEMINI_FIELD_NOTE_SYSTEM.format(
            signal_firewall=SIGNAL_FIREWALL_INSTRUCTIONS,
        )

    return GEMINI_SYSTEM_INSTRUCTION.format(
        signal_firewall=SIGNAL_FIREWALL_INSTRUCTIONS,
    )


def _build_prospect_context(
    intent_profile: ProspectIntent,
    prospect_data: dict[str, Any] | None = None,
) -> str:
    # Build prospect context string for the prompt
    # Separates public and private signals explicitly

    parts = ["## Prospect Context\n"]

    # Public context (safe to reference in email)
    parts.append("### PUBLIC (safe to reference in the email)")
    if prospect_data:
        if prospect_data.get("contact_name"):
            parts.append(f"- Recipient name: {prospect_data['contact_name']}")
            # Extract first name for greeting
            first_name = prospect_data["contact_name"].split()[0]
            parts.append(f"- First name (for greeting): {first_name}")
        if prospect_data.get("company_name"):
            parts.append(f"- Company: {prospect_data['company_name']}")
        if prospect_data.get("industry"):
            parts.append(f"- Industry: {prospect_data['industry']}")
        if prospect_data.get("job_title"):
            parts.append(f"- Role: {prospect_data['job_title']}")
        if prospect_data.get("employee_count"):
            parts.append(
                f"- Scale: {prospect_data['employee_count']} "
                "(use scale-aware wording, don't cite exact numbers)"
            )

    # Sender info — hardcoded placeholder until campaign settings provide it
    parts.append("- Sender name: [Sender Name]")
    parts.append(
        "  (Use exactly '[Sender Name]' as the sender. "
        "Do NOT invent a first name like 'Alex' or 'Sam'.)"
    )

    # Private context (topic selection only)
    parts.append("\n### PRIVATE (use ONLY to choose topic/angle — NEVER mention in email)")
    parts.append(f"- Room: {intent_profile.current_room.value}")
    parts.append(f"- Lead score: {intent_profile.lead_score}")
    if intent_profile.service_area:
        parts.append(f"- Service area interest: {intent_profile.service_area}")
    if intent_profile.related_areas:
        parts.append(f"- Related areas: {', '.join(intent_profile.related_areas)}")
    if intent_profile.pain_points:
        for pp in intent_profile.pain_points[:3]:
            if hasattr(pp, "description"):
                parts.append(f"- Pain point: {pp.description}")
            else:
                parts.append(f"- Pain point: {pp}")
    if prospect_data and prospect_data.get("pages_visited"):
        parts.append(f"- Pages visited: {prospect_data['pages_visited']}")

    return "\n".join(parts)


def _build_content_context(
    selected_content: ContentAsset | dict[str, Any] | None,
) -> str:
    # Build content context for the prompt

    if not selected_content:
        return "## Content\nNo specific content link provided. Focus on general engagement."

    content_dict = selected_content if isinstance(selected_content, dict) else {}
    if hasattr(selected_content, "model_dump"):
        content_dict = selected_content.model_dump()

    context_parts = ["## Content to Include\n"]
    context_parts.append(f"- Title: {content_dict.get('title', 'Resource')}")

    url = content_dict.get("url", "")
    if url:
        context_parts.append(f"- URL: {url}")

    context_parts.append(f"- Type: {content_dict.get('content_type', 'article')}")

    if content_dict.get("summary"):
        context_parts.append(f"- Summary: {content_dict['summary']}")

    # Include full article body when available (for grounded insights)
    article_body = content_dict.get("article_body")
    if article_body:
        context_parts.append(
            "\n## Full Article Content (use to ground ALL claims in the email)\n"
        )
        context_parts.append(article_body)
        context_parts.append(
            "\nIMPORTANT: Every claim, quick test, and small move in your email "
            "MUST be grounded in the article content above. Do not invent facts."
        )

    if url:
        context_parts.append(
            f"\nInclude this URL as plain text in the email body: {url}"
            "\nDo NOT wrap it in markdown link syntax [text](url)."
        )
    else:
        context_parts.append(
            "\nNo content link available. Write a standalone insight email "
            "grounded in the title and summary above. Do NOT fabricate a URL."
        )

    return "\n".join(context_parts)


def _build_insight_context(
    content_insights: dict[str, Any] | None,
) -> str:
    # Build insight context block for the prompt

    if not content_insights or not content_insights.get("insights"):
        return ""

    parts = ["\n## Grounded Insights (use for quick tests and small moves)\n"]

    core_reframe = content_insights.get("core_reframe")
    if core_reframe:
        parts.append(f"Core reframe: {core_reframe}")

    problem_theme = content_insights.get("problem_theme")
    if problem_theme:
        parts.append(f"Problem theme: {problem_theme}")

    parts.append("\nInsights to draw from:")
    for i, insight in enumerate(content_insights["insights"][:12], 1):
        insight_text = insight.get("insight", "")
        insight_type = insight.get("type", "")
        parts.append(f"{i}. [{insight_type}] {insight_text}")

    parts.append(
        "\nBuild your quick tests and small moves from these insights. "
        "Do not invent claims not grounded here."
    )

    return "\n".join(parts)


def _build_room_guardrails(room: Room) -> str:
    # Build explicit guardrails reminder for the room

    if room == Room.PROBLEM:
        return """## CRITICAL Room Guardrails (PROBLEM ROOM)
⛔ DO NOT: Use company name, "we", "our", or any first-person company references
⛔ DO NOT: Mention products, services, solutions, or offerings
⛔ DO NOT: Include pricing, demos, calls, or sales CTAs
⛔ DO NOT: Use urgency tactics or scarcity language
⛔ DO NOT: Reference website visits, tracking, or how you found them
⛔ DO NOT: Use markdown formatting — bold (**text**), [link](url), or any other markup
✅ DO: Focus purely on the problem and education
✅ DO: Use neutral, third-person perspective
✅ DO: Be a helpful peer, not a salesperson
✅ DO: Write URLs as plain text (e.g. https://example.com/article)"""

    elif room == Room.SOLUTION:
        return """## Room Guardrails (SOLUTION ROOM)
⛔ DO NOT: Push for demos or pricing discussions
⛔ DO NOT: Use aggressive sales language or urgency
⛔ DO NOT: Reference website visits or tracking
⛔ DO NOT: Use markdown formatting — write URLs as plain text
⚠️ MAY: Reference "organizations like ours" softly
⚠️ MAY: Mention company expertise in passing
✅ DO: Focus on educational value and approaches
✅ DO: Reference case studies and how-to guidance
✅ DO: Offer to discuss, not to sell"""

    else:  # OFFER
        return """## Room Guardrails (OFFER ROOM)
✅ MAY: Discuss company offerings directly
✅ MAY: Include demo or meeting requests
✅ MAY: Reference pricing or proposals
✅ MAY: Use ROI and value language
⛔ DO NOT: Reference website visits or tracking
⛔ DO NOT: Use markdown formatting — write URLs as plain text
⚠️ STILL: Maintain helpful tone, not pushy
⛔ DO NOT: Use aggressive urgency or manipulation"""


def _get_generation_config(room: Room) -> dict[str, Any]:
    # Get room-appropriate generation configuration
    # max_output_tokens is always 16384 (model produces shorter output via prompt)

    config = DEFAULT_GENERATION_CONFIG.copy()

    if room in ROOM_GENERATION_OVERRIDES:
        config.update(ROOM_GENERATION_OVERRIDES[room])

    return config


# ============================================================================
# Main Assembly Function
# ============================================================================

def assemble_email_context(
    intent_profile: ProspectIntent,
    prompt_components: dict[str, str],
    selected_content: ContentAsset | None = None,
    prospect_data: dict[str, Any] | None = None,
    content_insights: dict[str, Any] | None = None,
    email_format: str | None = None,
) -> dict[str, Any]:
    # Assemble complete context for Gemini email generation
    # Returns dict with prompt, system_instruction, and generation_config

    room = intent_profile.current_room

    # Determine email format
    if email_format is None:
        email_format = (
            EMAIL_FORMAT_FIELD_NOTE if room == Room.PROBLEM
            else EMAIL_FORMAT_STANDARD
        )

    logger.info(
        "Assembling email context",
        extra={
            "prospect_id": intent_profile.prospect_id,
            "room": room.value,
            "format": email_format,
            "has_content": selected_content is not None,
            "has_insights": content_insights is not None,
        }
    )

    # Assemble the full prompt from components
    full_prompt = assemble_full_prompt(prompt_components, email_format)

    # Add prospect context
    prospect_context = _build_prospect_context(intent_profile, prospect_data)
    full_prompt += "\n\n" + prospect_context

    # Add content context
    content_context = _build_content_context(selected_content)
    full_prompt += "\n\n" + content_context

    # Add insight context (if available)
    insight_context = _build_insight_context(content_insights)
    if insight_context:
        full_prompt += "\n\n" + insight_context

    # Add room guardrails
    guardrails = _build_room_guardrails(room)
    full_prompt += "\n\n" + guardrails

    # Get system instruction
    system_instruction = _get_system_instruction(room, email_format)

    # Get generation config
    generation_config = _get_generation_config(room)

    return {
        "prompt": full_prompt,
        "system_instruction": system_instruction,
        "generation_config": generation_config,
        "metadata": {
            "prospect_id": intent_profile.prospect_id,
            "room": room.value,
            "email_format": email_format,
            "has_content": selected_content is not None,
            "has_insights": content_insights is not None,
            "timestamp": datetime.now().isoformat(),
        },
    }


# ============================================================================
# Validation
# ============================================================================

def validate_context(context: dict[str, Any]) -> tuple[bool, list[str]]:
    # Validate assembled context before sending to Gemini

    issues: list[str] = []

    if not context.get("prompt"):
        issues.append("Missing prompt")
    if not context.get("system_instruction"):
        issues.append("Missing system_instruction")
    if not context.get("generation_config"):
        issues.append("Missing generation_config")

    # Check prompt length (Gemini has token limits)
    prompt = context.get("prompt", "")
    if len(prompt) > 100000:
        issues.append(f"Prompt too long: {len(prompt)} chars")

    # Check generation config has required fields
    gen_config = context.get("generation_config", {})
    if "max_output_tokens" not in gen_config:
        issues.append("Missing max_output_tokens in generation_config")
    if "temperature" not in gen_config:
        issues.append("Missing temperature in generation_config")

    # Check metadata
    metadata = context.get("metadata", {})
    if not metadata.get("room"):
        issues.append("Missing room in metadata")

    return len(issues) == 0, issues


# ============================================================================
# LangGraph Node Function
# ============================================================================

def assemble_context(state: AgentState) -> dict[str, Any]:
    # LangGraph node function for email context assembly
    # Reads: intent_profile, prompt_components, selected_content,
    #        prospect_data, content_insights
    # Writes: generation_config

    intent_profile = state.get("intent_profile")
    prompt_components = state.get("prompt_components")

    # Validate required inputs
    if not intent_profile:
        logger.error("No intent_profile in state")
        return {
            "generation_config": None,
            "error": "Missing intent_profile in state",
        }

    if not prompt_components:
        logger.error("No prompt_components in state")
        return {
            "generation_config": None,
            "error": "Missing prompt_components in state - run build_template first",
        }

    # Convert Pydantic model if needed
    if hasattr(intent_profile, "model_dump"):
        pass  # Already a Pydantic model
    elif isinstance(intent_profile, dict):
        from models.prospect import ProspectIntent, determine_room
        intent_profile = ProspectIntent(
            prospect_id=intent_profile.get("prospect_id", 0),
            current_room=determine_room(intent_profile.get("lead_score", 0)),
            lead_score=intent_profile.get("lead_score", 0),
            service_area=intent_profile.get("service_area"),
            related_areas=intent_profile.get("related_areas", []),
            confidence=intent_profile.get("confidence", 0.5),
        )

    selected_content = state.get("selected_content")
    prospect_data = state.get("prospect_data")
    content_insights = state.get("content_insights")
    email_format = state.get("email_format")

    # Convert prospect_data to dict if needed
    if prospect_data and hasattr(prospect_data, "model_dump"):
        prospect_data = prospect_data.model_dump()

    # Assemble the context
    context = assemble_email_context(
        intent_profile=intent_profile,
        prompt_components=prompt_components,
        selected_content=selected_content,
        prospect_data=prospect_data,
        content_insights=content_insights,
        email_format=email_format,
    )

    # Validate the assembled context
    is_valid, issues = validate_context(context)

    if not is_valid:
        logger.warning(
            "Context validation issues",
            extra={
                "prospect_id": intent_profile.prospect_id,
                "issues": issues,
            }
        )
        # Continue anyway but note the issues
        context["metadata"]["validation_issues"] = issues

    return {
        "generation_config": context,
        "current_step": "context_assembled",
    }
