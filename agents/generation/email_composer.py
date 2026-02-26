# =============================================================================
# Email Composer Agent
# =============================================================================
#
# Generates personalized outreach emails using Gemini API based on:
# - Prospect intent profile (from Phase 3 intent_summarizer)
# - Selected content asset (from Phase 2 asset_ranker)
# - Prospect firmographic data
# - Room-specific tone guidelines (RTR methodology)
#
# Phase 5: Uses Gemini for creative email generation.
# Falls back to a template-based approach when Gemini is unavailable.
#
# The email is placed into state["generated_email"] for the guardrail
# inspector (Phase 4) to validate before delivery.
# =============================================================================

import logging
from typing import Any

from config.settings import settings
from models.state import AgentState, ProspectIntent, RankedAsset

logger = logging.getLogger(__name__)

# =============================================================================
# Room-Specific Tone Guidelines
# =============================================================================

ROOM_TONE = {
    "problem": (
        "Empathetic and educational. Focus on the prospect's challenges "
        "without mentioning your company or solutions. Use 'you' and 'your' "
        "language. Reference industry-specific pain points. No CTAs, no pricing, "
        "no company references."
    ),
    "solution": (
        "Informative and consultative. You may gently reference how similar "
        "organizations have solved these challenges. Soft company references "
        "are acceptable but avoid hard sells. No pricing, no aggressive CTAs."
    ),
    "offer": (
        "Direct and value-focused. You may include company references, "
        "pricing context, and clear calls to action like scheduling a demo. "
        "Stay professional \u2014 no aggressive or scarcity-based tactics."
    ),
}

# =============================================================================
# System Prompt for Gemini
# =============================================================================

EMAIL_SYSTEM_PROMPT = """\
You are an expert B2B email copywriter specializing in the Reading Room (RTR) \
methodology. You craft personalized outreach emails that are:
- Tailored to the prospect's industry, role, and pain points
- Appropriate for their current buying stage (room)
- Natural and conversational, never robotic or generic
- Concise (150-250 words for the body)

You MUST follow these rules:
1. Write ONLY the email body \u2014 no subject line, no greeting, no signature
2. The email will be wrapped with a greeting and signature separately
3. Follow the room-specific tone guidelines exactly
4. Reference the provided content asset naturally (as a resource, not a pitch)
5. Never use superlatives like "best", "leading", "#1", or "world-class"
6. Never mention competitors by name
7. Never use aggressive sales tactics or scarcity language

Return ONLY the email body text \u2014 no markdown, no formatting instructions.
"""


# =============================================================================
# LangGraph Node
# =============================================================================

async def compose_email(state: AgentState) -> dict[str, Any]:
    """Generate a personalized email using Gemini or template fallback.

    Reads: prospect_data, intent_profile, selected_content
    Returns: generated_email, email_context
    """

    prospect_id = state.get("prospect_id", 0)
    prospect_data = state.get("prospect_data", {})
    intent_profile = state.get("intent_profile")
    selected_content = state.get("selected_content")

    logger.info(
        "Composing email",
        extra={
            "prospect_id": prospect_id,
            "has_intent": intent_profile is not None,
            "has_content": selected_content is not None,
        },
    )

    if not intent_profile or not selected_content:
        logger.warning(
            "Missing intent_profile or selected_content, skipping email generation",
            extra={"prospect_id": prospect_id},
        )
        return {
            "generated_email": None,
            "email_context": None,
            "current_step": "compose_email",
        }

    room = prospect_data.get("current_room", "problem")

    # Build email context dict for downstream use
    email_context = _build_email_context(prospect_data, intent_profile, selected_content, room)

    # Try Gemini first, fall back to template
    email_body = None

    if settings.has_gemini_key:
        email_body = await _compose_with_gemini(email_context, room)

    if email_body is None:
        email_body = _compose_with_template(email_context, room)

    logger.info(
        "Email composition complete",
        extra={
            "prospect_id": prospect_id,
            "room": room,
            "source": "gemini" if settings.has_gemini_key and email_body else "template",
            "length": len(email_body) if email_body else 0,
        },
    )

    return {
        "generated_email": email_body,
        "email_context": email_context,
        "current_step": "compose_email",
    }


# =============================================================================
# Gemini Email Generation (Phase 5)
# =============================================================================

async def _compose_with_gemini(
    email_context: dict[str, Any],
    room: str,
) -> str | None:
    """Use Gemini API for creative email generation. Returns None on failure."""

    try:
        from services.llm_client import GeminiClient, LLMClientError

        user_message = _build_gemini_prompt(email_context, room)

        async with GeminiClient() as gemini:
            email_body = await gemini.complete_text(
                system=EMAIL_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.7,
            )

        # Clean up any markdown or extra whitespace
        email_body = email_body.strip()

        # Remove any subject line the model may have added
        if email_body.lower().startswith("subject:"):
            lines = email_body.split("\n", 1)
            email_body = lines[1].strip() if len(lines) > 1 else email_body

        logger.info("Gemini email generation succeeded")
        return email_body

    except LLMClientError as e:
        logger.warning(
            f"Gemini email generation failed, falling back to template: {e}",
            extra={"provider": e.provider},
        )
        return None
    except Exception as e:
        logger.warning(
            f"Unexpected error in Gemini email generation: {e}",
        )
        return None


def _build_gemini_prompt(email_context: dict[str, Any], room: str) -> str:
    """Build the user-message prompt for Gemini with all context."""

    tone = ROOM_TONE.get(room, ROOM_TONE["problem"])

    parts = [
        f"Write a personalized B2B outreach email body for this prospect.\n",
        f"ROOM: {room}",
        f"TONE GUIDELINES: {tone}\n",
        f"PROSPECT:",
        f"  Name: {email_context.get('contact_name', 'Unknown')}",
        f"  Title: {email_context.get('job_title', 'Unknown')}",
        f"  Company: {email_context.get('company_name', 'Unknown')}",
        f"  Industry: {email_context.get('industry', 'Unknown')}",
    ]

    pain_points = email_context.get("pain_points", [])
    if pain_points:
        parts.append(f"  Pain Points: {', '.join(pain_points)}")

    urgency = email_context.get("urgency_level")
    if urgency:
        parts.append(f"  Urgency: {urgency}")

    stage = email_context.get("decision_stage")
    if stage:
        parts.append(f"  Buying Stage: {stage}")

    questions = email_context.get("key_questions", [])
    if questions:
        parts.append(f"  Likely Questions: {', '.join(questions)}")

    parts.append(f"\nCONTENT ASSET TO REFERENCE:")
    parts.append(f"  Title: {email_context.get('content_title', 'Unknown')}")
    parts.append(f"  URL: {email_context.get('content_url', '')}")
    parts.append(f"  Room: {email_context.get('content_room', room)}")

    parts.append(f"\nWrite the email body now. Remember: body text only, no subject, no greeting, no signature.")

    return "\n".join(parts)


# =============================================================================
# Template-Based Fallback
# =============================================================================

def _compose_with_template(
    email_context: dict[str, Any],
    room: str,
) -> str:
    """Generate email from templates when Gemini is unavailable."""

    logger.info("Using template-based email generation")

    contact_name = email_context.get("contact_name", "there")
    first_name = contact_name.split()[0] if contact_name != "there" else "there"
    company = email_context.get("company_name", "your organization")
    industry = email_context.get("industry", "your industry")
    content_title = email_context.get("content_title", "a relevant resource")
    content_url = email_context.get("content_url", "")
    pain_points = email_context.get("pain_points", [])

    primary_pain = pain_points[0] if pain_points else "operational challenges"

    if room == "problem":
        return (
            f"I've been researching trends in the {industry.lower()} space and "
            f"noticed that many organizations like {company} are grappling with "
            f"{primary_pain.lower()}.\n\n"
            f"I came across this resource that explores this challenge in depth: "
            f'"{ content_title}"\n{content_url}\n\n'
            f"It covers some of the patterns we're seeing across the industry "
            f"and the real cost of leaving these issues unaddressed.\n\n"
            f"Thought it might be relevant given your role. Would love to hear "
            f"your perspective on how this resonates with what you're seeing at {company}."
        )
    elif room == "solution":
        return (
            f"Following up on the challenges around {primary_pain.lower()} that "
            f"many {industry.lower()} organizations face \u2014 I wanted to share a "
            f"resource that outlines how similar companies have approached this.\n\n"
            f'"{ content_title}"\n{content_url}\n\n'
            f"It walks through practical approaches that have worked for teams "
            f"in similar situations. The strategies may be applicable to what "
            f"you're working on at {company}.\n\n"
            f"Happy to discuss any of the approaches covered if they spark ideas."
        )
    else:  # offer
        return (
            f"Based on our previous conversations about {primary_pain.lower()}, "
            f"I wanted to share a concrete path forward.\n\n"
            f'"{ content_title}"\n{content_url}\n\n'
            f"This outlines a proven approach that could help {company} address "
            f"these challenges. Organizations similar to yours in {industry.lower()} "
            f"have seen meaningful results with this strategy.\n\n"
            f"Would it make sense to schedule a brief call to discuss how this "
            f"could apply to your specific situation?"
        )


# =============================================================================
# Standalone generation (for testing or direct use)
# =============================================================================

def compose_email_from_context(
    email_context: dict[str, Any],
    room: str,
) -> str:
    """Generate an email from context dict using templates.

    Useful for testing without the full graph workflow.

    Args:
        email_context: Dict with contact_name, company_name, industry,
                       content_title, content_url, pain_points, etc.
        room: RTR room (problem, solution, offer).

    Returns:
        Email body text.
    """
    return _compose_with_template(email_context, room)


# =============================================================================
# Helpers
# =============================================================================

def _build_email_context(
    prospect_data: dict[str, Any],
    intent_profile: ProspectIntent,
    selected_content: RankedAsset,
    room: str,
) -> dict[str, Any]:
    """Build a flat context dict from state components."""

    return {
        "contact_name": prospect_data.get("contact_name", "Unknown"),
        "job_title": prospect_data.get("job_title", "Unknown"),
        "company_name": prospect_data.get("company_name", "Unknown"),
        "industry": prospect_data.get("industry", "Unknown"),
        "room": room,
        "service_area": intent_profile.service_area,
        "pain_points": intent_profile.pain_points,
        "confidence": intent_profile.confidence,
        "urgency_level": intent_profile.urgency_level,
        "decision_stage": intent_profile.decision_stage,
        "key_questions": intent_profile.key_questions,
        "content_title": selected_content.title,
        "content_url": selected_content.url,
        "content_room": selected_content.room,
        "content_score": selected_content.score,
    }
