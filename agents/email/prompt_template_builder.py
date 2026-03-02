# agents/email/prompt_template_builder.py
# Prompt Template Builder Agent (#17)
# Assembles 7-component prompts for email generation based on room and intent
# Updated: Field Note scaffold, angle rotation, word count enforcement,
#          private/public signal firewall
# Templates live in agents/email/room_templates.py

from __future__ import annotations

import logging
from typing import Any

from models.state import AgentState, ContentAsset
from models.prospect import ProspectIntent, Room
from agents.email.room_templates import (
    EMAIL_FORMAT_FIELD_NOTE,
    EMAIL_FORMAT_STANDARD,
    PROBLEM_ROOM_FIELD_NOTE_TEMPLATES,
    PROBLEM_ROOM_STANDARD_TEMPLATES,
    SOLUTION_ROOM_TEMPLATES,
    OFFER_ROOM_TEMPLATES,
    WORD_COUNT_INSTRUCTIONS,
    SIGNAL_FIREWALL_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Angle Rotation for Series
# ============================================================================

def get_angle_for_week(
    week_number: int,
    used_angles: list[str] | None = None,
) -> dict[str, str]:
    # Get the recommended angle for a given week number
    # Rotates through the angle library, skipping already-used angles

    from config.field_note_spec import FIELD_NOTE_ANGLES

    available = FIELD_NOTE_ANGLES.copy()

    if used_angles:
        available = [a for a in available if a["id"] not in used_angles]

    if not available:
        available = FIELD_NOTE_ANGLES.copy()

    index = (week_number - 1) % len(available)
    return available[index]


# ============================================================================
# Template Selection
# ============================================================================

def _get_base_template(
    room: Room,
    email_format: str = EMAIL_FORMAT_FIELD_NOTE,
) -> dict[str, str]:
    # Get the base template components for a room + format combination

    if room == Room.PROBLEM:
        if email_format == EMAIL_FORMAT_FIELD_NOTE:
            return PROBLEM_ROOM_FIELD_NOTE_TEMPLATES
        return PROBLEM_ROOM_STANDARD_TEMPLATES
    elif room == Room.SOLUTION:
        return SOLUTION_ROOM_TEMPLATES
    else:
        return OFFER_ROOM_TEMPLATES


# ============================================================================
# Personalization Helpers
# ============================================================================

def _personalize_pain_framing(
    base_framing: str,
    intent_profile: ProspectIntent,
) -> str:
    # Inject actual pain points into the framing instructions

    if not intent_profile.pain_points:
        return base_framing

    pain_context = "\n\nProspect's identified pain points:\n"
    for pp in intent_profile.pain_points[:3]:
        if hasattr(pp, "description"):
            pain_context += f"- {pp.description}"
            if hasattr(pp, "severity"):
                pain_context += f" (severity: {pp.severity})"
            pain_context += "\n"
        else:
            pain_context += f"- {pp}\n"

    pain_context += "\nAddress these specific pains in the email."
    return base_framing + pain_context


def _personalize_content_integration(
    base_integration: str,
    selected_content: ContentAsset | dict[str, Any] | None,
) -> str:
    # Add content details to integration instructions

    if not selected_content:
        return base_integration + "\n\nNo specific content link provided. Focus on general engagement."

    content_dict = selected_content if isinstance(selected_content, dict) else {}
    if hasattr(selected_content, "model_dump"):
        content_dict = selected_content.model_dump()

    context_parts = ["## Content to Include\n"]
    context_parts.append(f"- Title: {content_dict.get('title', 'Resource')}")
    context_parts.append(f"- URL: {content_dict.get('url', '')}")
    context_parts.append(f"- Type: {content_dict.get('content_type', 'article')}")

    if content_dict.get("summary"):
        context_parts.append(f"- Summary: {content_dict['summary']}")

    context_parts.append("\nIntegrate this link naturally in the email body.")
    return "\n".join(context_parts)


def _add_personalization_context(
    components: dict[str, str],
    intent_profile: ProspectIntent,
    prospect_data: dict[str, Any] | None = None,
) -> dict[str, str]:
    # Add prospect-specific personalization context to components
    # Separates PUBLIC (safe to mention) from PRIVATE (topic selection only)

    if not prospect_data:
        return components

    # PUBLIC context block (safe to mention in the email)
    public_parts = ["\n\n## Prospect Context (PUBLIC — safe to reference)"]
    if prospect_data.get("company_name"):
        public_parts.append(f"- Company: {prospect_data['company_name']}")
    if prospect_data.get("industry"):
        public_parts.append(f"- Industry: {prospect_data['industry']}")
    if prospect_data.get("job_title"):
        public_parts.append(f"- Role: {prospect_data['job_title']}")
    if prospect_data.get("contact_name"):
        public_parts.append(f"- Name: {prospect_data['contact_name']}")
    if prospect_data.get("employee_count"):
        public_parts.append(
            f"- Scale: {prospect_data['employee_count']} "
            "(use scale-aware language, don't cite exact numbers)"
        )

    # PRIVATE context block (topic selection only — never mention in email)
    private_parts = [
        "\n\n## Prospect Signals (PRIVATE — topic/angle selection ONLY, "
        "DO NOT mention in email)"
    ]
    if intent_profile.service_area:
        private_parts.append(f"- Service area interest: {intent_profile.service_area}")
    if intent_profile.related_areas:
        private_parts.append(f"- Related areas: {', '.join(intent_profile.related_areas)}")
    if prospect_data.get("pages_visited"):
        private_parts.append(f"- Pages visited: {prospect_data['pages_visited']}")
    if prospect_data.get("lead_score"):
        private_parts.append(f"- Lead score: {prospect_data['lead_score']}")

    components["value_positioning"] = (
        components["value_positioning"]
        + "\n".join(public_parts)
        + "\n".join(private_parts)
    )
    return components


def _add_insight_context(
    components: dict[str, str],
    content_insights: dict[str, Any] | None,
) -> dict[str, str]:
    # Add extracted insights to pain framing for specificity

    if not content_insights or not content_insights.get("insights"):
        return components

    insights = content_insights["insights"]
    core_reframe = content_insights.get("core_reframe", "")
    problem_theme = content_insights.get("problem_theme", "")

    block = "\n\n## Grounded Insights (use these for specificity)\n"
    if core_reframe:
        block += f"Core reframe: {core_reframe}\n"
    if problem_theme:
        block += f"Problem theme: {problem_theme}\n"

    block += "\nAvailable insights to draw from:\n"
    for i, insight in enumerate(insights[:12], 1):
        block += f"{i}. [{insight.get('type', '')}] {insight.get('insight', '')}\n"

    block += (
        "\nUse these to build specific quick tests and small moves. "
        "Do not invent claims not grounded in these insights."
    )
    components["pain_framing"] = components["pain_framing"] + block
    return components


def _add_angle_context(
    components: dict[str, str],
    angle: dict[str, str] | None,
) -> dict[str, str]:
    # Add angle rotation context for series emails

    if not angle:
        return components

    block = f"""

## This Week's Angle: {angle.get('label', 'General')}
{angle.get('description', '')}

Frame the entire email through this lens. The reframe, quick test, and small moves
should all connect to this angle."""

    components["pain_framing"] = components["pain_framing"] + block
    return components


# ============================================================================
# Main Builder Function
# ============================================================================

def build_prompt_template(
    intent_profile: ProspectIntent,
    selected_content: ContentAsset | dict[str, Any] | None = None,
    prospect_data: dict[str, Any] | None = None,
    email_format: str = EMAIL_FORMAT_FIELD_NOTE,
    content_insights: dict[str, Any] | None = None,
    angle: dict[str, str] | None = None,
    week_number: int | None = None,
) -> dict[str, str]:
    # Build a complete 7-component prompt template

    room = intent_profile.current_room

    logger.info(
        "Building prompt template",
        extra={
            "prospect_id": intent_profile.prospect_id,
            "room": room.value,
            "format": email_format,
            "service_area": intent_profile.service_area,
            "has_insights": content_insights is not None,
            "angle": angle.get("id") if angle else None,
        }
    )

    # Auto-select angle if week_number provided but no explicit angle
    if week_number and not angle and email_format == EMAIL_FORMAT_FIELD_NOTE:
        angle = get_angle_for_week(week_number)

    # Start with base template for room + format
    components = _get_base_template(room, email_format).copy()

    # Personalize pain framing with actual pain points
    components["pain_framing"] = _personalize_pain_framing(
        components["pain_framing"], intent_profile,
    )

    # Add content-specific integration guidance
    components["content_integration"] = _personalize_content_integration(
        components["content_integration"], selected_content,
    )

    # Add personalization context (public/private separation)
    components = _add_personalization_context(components, intent_profile, prospect_data)

    # Add extracted insights for specificity
    components = _add_insight_context(components, content_insights)

    # Add angle context for series rotation
    components = _add_angle_context(components, angle)

    # Add service area context if available
    if intent_profile.service_area:
        service_context = f"\n\nService area focus: {intent_profile.service_area}"
        if intent_profile.related_areas:
            service_context += f"\nRelated areas: {', '.join(intent_profile.related_areas)}"
        components["value_positioning"] = components["value_positioning"] + service_context

    # Add urgency context if signals present (Offer room only)
    if room == Room.OFFER and intent_profile.urgency_signals:
        urgency_context = "\n\nUrgency signals detected:\n"
        for signal in intent_profile.urgency_signals[:3]:
            urgency_context += f"- {signal}\n"
        urgency_context += "Consider acknowledging timeline sensitivity appropriately."
        components["cta_approach"] = components["cta_approach"] + urgency_context

    logger.info(
        "Prompt template built",
        extra={
            "prospect_id": intent_profile.prospect_id,
            "components": list(components.keys()),
        }
    )

    return components


def assemble_full_prompt(
    components: dict[str, str],
    email_format: str = EMAIL_FORMAT_FIELD_NOTE,
) -> str:
    # Assemble all 7 components into a single generation prompt

    sections = [
        ("SUBJECT LINE GUIDANCE", "subject_guidance"),
        ("OPENING STYLE", "opening_style"),
        ("PAIN POINT FRAMING", "pain_framing"),
        ("VALUE POSITIONING", "value_positioning"),
        ("CONTENT INTEGRATION", "content_integration"),
        ("CREDIBILITY ELEMENTS", "credibility_elements"),
        ("CALL-TO-ACTION APPROACH", "cta_approach"),
    ]

    prompt_parts = ["# Email Generation Instructions\n"]
    prompt_parts.append("Follow these guidelines to generate a personalized email:\n")

    # Add signal firewall at the top
    prompt_parts.append(SIGNAL_FIREWALL_INSTRUCTIONS)

    # Add word count instructions
    word_count = WORD_COUNT_INSTRUCTIONS.get(email_format, "")
    if word_count:
        prompt_parts.append(word_count)

    for section_title, component_key in sections:
        content = components.get(component_key, "")
        prompt_parts.append(f"\n## {section_title}\n{content}")

    prompt_parts.append("\n\n---\n")
    prompt_parts.append("Generate the email now, following all guidelines above.")
    prompt_parts.append("Output format: JSON with 'subject' and 'body' keys.")
    prompt_parts.append(
        "The 'body' key should contain the complete email text "
        "(plain text, not HTML)."
    )

    return "\n".join(prompt_parts)


# ============================================================================
# LangGraph Node Function
# ============================================================================

def build_template(state: AgentState) -> dict[str, Any]:
    # LangGraph node function for prompt template building
    # Reads: intent_profile, selected_content, prospect_data, content_insights
    # Writes: prompt_components

    intent_profile = state.get("intent_profile")

    if not intent_profile:
        logger.error("No intent_profile in state")
        return {
            "prompt_components": None,
            "error": "Missing intent_profile in state",
        }

    # Convert Pydantic model if needed
    if hasattr(intent_profile, "model_dump"):
        pass
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

    # Convert prospect_data to dict if needed
    if prospect_data and hasattr(prospect_data, "model_dump"):
        prospect_data = prospect_data.model_dump()

    # Determine email format based on room
    email_format = EMAIL_FORMAT_FIELD_NOTE
    if intent_profile.current_room != Room.PROBLEM:
        email_format = EMAIL_FORMAT_STANDARD

    # Allow override from state
    if state.get("email_format"):
        email_format = state["email_format"]

    # Get week number for angle rotation (if in series mode)
    week_number = state.get("week_number")

    components = build_prompt_template(
        intent_profile=intent_profile,
        selected_content=selected_content,
        prospect_data=prospect_data,
        email_format=email_format,
        content_insights=content_insights,
        week_number=week_number,
    )

    return {
        "prompt_components": components,
        "current_step": "template_built",
    }
