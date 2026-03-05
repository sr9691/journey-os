# =============================================================================
# Lead Intent Summarizer Agent
# =============================================================================
#
# Analyzes prospect data to extract intent signals:
# - Service area interest based on page visits and engagement
# - Pain points from engagement patterns and firmographics
# - Confidence score for recommendation quality
#
# Phase 3: Uses Claude API for richer prospect understanding when available.
# Falls back to rule-based extraction when Claude is unavailable.
# Structured logging tracks which analysis path was taken.
# =============================================================================

import logging
from typing import Any

from config.settings import settings
from models.state import AgentState, ProspectIntent

logger = logging.getLogger(__name__)

# System prompt for Claude intent analysis
INTENT_SYSTEM_PROMPT = """\
You are an intent analysis engine for B2B marketing automation. You analyze \
prospect firmographics, engagement data, and behavioral signals to determine \
their likely service area interest, pain points, and buying stage.

You must respond with ONLY a JSON object (no markdown, no explanation) with \
exactly these fields:

{
  "service_area": "one of: ai-development, cloud-migration, data-analytics, cloud-modernization, or null if unclear",
  "pain_points": ["list of 2-4 specific pain points based on the prospect's signals"],
  "confidence": 0.0 to 1.0,
  "urgency_level": "low, medium, or high",
  "decision_stage": "awareness, consideration, or decision",
  "key_questions": ["1-3 questions the prospect likely has based on their signals"]
}

Guidelines:
- service_area: Infer from page visits, industry, and job title. Use null only if truly ambiguous.
- pain_points: Be specific to the prospect's industry and role. Avoid generic statements.
- confidence: Higher if multiple signals align (engagement + industry + title).
- urgency_level: "high" if lead_score > 50 or days_in_room > 14, "low" if lead_score < 20.
- decision_stage: "awareness" for problem room, "consideration" for solution, "decision" for offer.
- key_questions: What would this persona in this industry likely want to know?
"""


async def analyze_intent(state: AgentState) -> dict[str, Any]:
    """Analyze prospect data to determine intent signals.

    Reads: prospect_id, prospect_data
    Returns: intent_profile

    Phase 3: Uses Gemini API for richer prospect understanding when available.
    Falls back to rule-based extraction when Gemini is unavailable.
    """

    prospect_id = state["prospect_id"]
    prospect_data = state.get("prospect_data")

    logger.info(
        "Analyzing intent",
        extra={"prospect_id": prospect_id, "has_data": prospect_data is not None},
    )

    if not prospect_data:
        logger.error("No prospect_data in state")
        return {
            "intent_profile": None,
            "error": "Missing prospect_data in state",
        }

    # Try Claude API first, fall back to rules
    intent_profile = None

    if settings.has_anthropic_key:
        intent_profile = await _analyze_with_claude(prospect_id, prospect_data)

    if settings.has_gemini_key:
        intent_profile = await _analyze_with_gemini(prospect_id, prospect_data)    
    
    if intent_profile is None:
        intent_profile = _analyze_with_rules(prospect_id, prospect_data)

    logger.info(
        "Intent analysis complete",
        extra={
            "prospect_id": prospect_id,
            "service_area": intent_profile.service_area,
            "pain_point_count": len(intent_profile.pain_points),
            "confidence": intent_profile.confidence,
            "source": intent_profile.analysis_source,
            "urgency": intent_profile.urgency_level,
            "stage": intent_profile.decision_stage,
        },
    )

    return {"intent_profile": intent_profile}


# =============================================================================
# Claude API Analysis (Phase 3)
# =============================================================================

async def _analyze_with_claude(
    prospect_id: int,
    prospect_data: dict[str, Any],
) -> ProspectIntent | None:
    """Use Claude API for rich intent analysis. Returns None on failure."""

    try:
        from services.llm_client import ClaudeClient, LLMClientError

        # Build the user message with prospect signals
        user_message = _build_claude_prompt(prospect_data)

        async with ClaudeClient() as claude:
            result = await claude.complete_json(
                system=INTENT_SYSTEM_PROMPT,
                user_message=user_message,
            )

        # Validate and build ProspectIntent from Claude's response
        intent = ProspectIntent(
            prospect_id=prospect_id,
            service_area=result.get("service_area"),
            pain_points=result.get("pain_points", []),
            confidence=min(1.0, max(0.0, float(result.get("confidence", 0.5)))),
            urgency_level=result.get("urgency_level"),
            decision_stage=result.get("decision_stage"),
            key_questions=result.get("key_questions", []),
            analysis_source="claude",
        )

        logger.info(
            "Claude intent analysis succeeded",
            extra={"prospect_id": prospect_id},
        )
        return intent

    except LLMClientError as e:
        logger.warning(
            f"Claude intent analysis failed, falling back to rules: {e}",
            extra={"prospect_id": prospect_id, "provider": e.provider},
        )
        return None
    except Exception as e:
        logger.warning(
            f"Unexpected error in Claude analysis, falling back to rules: {e}",
            extra={"prospect_id": prospect_id},
        )
        return None


def _build_claude_prompt(prospect_data: dict[str, Any]) -> str:
    """Assemble prospect signals into a structured prompt for Claude."""

    parts = ["Analyze this B2B prospect and determine their intent:\n"]

    # Firmographics
    if prospect_data.get("company_name"):
        parts.append(f"Company: {prospect_data['company_name']}")
    if prospect_data.get("industry"):
        parts.append(f"Industry: {prospect_data['industry']}")
    if prospect_data.get("employee_count"):
        parts.append(f"Company Size: {prospect_data['employee_count']}")

    # Contact info
    if prospect_data.get("contact_name"):
        parts.append(f"Contact: {prospect_data['contact_name']}")
    if prospect_data.get("job_title"):
        parts.append(f"Title: {prospect_data['job_title']}")

    # RTR signals
    if prospect_data.get("current_room"):
        parts.append(f"Current Room: {prospect_data['current_room']}")
    if prospect_data.get("lead_score") is not None:
        parts.append(f"Lead Score: {prospect_data['lead_score']}")
    if prospect_data.get("days_in_room"):
        parts.append(f"Days in Room: {prospect_data['days_in_room']}")
    if prospect_data.get("email_sequence_position"):
        parts.append(f"Email Sequence Position: {prospect_data['email_sequence_position']}")

    # Engagement data
    if prospect_data.get("engagement_data"):
        parts.append(f"Recent Page Visits: {prospect_data['engagement_data']}")

    return "\n".join(parts)


# =============================================================================
# Gemini API Analysis (Phase 3)
# =============================================================================

async def _analyze_with_gemini(
    prospect_id: int,
    prospect_data: dict[str, Any],
) -> ProspectIntent | None:
    # Use Gemini API for rich intent analysis. Returns None on failure.

    try:
        from services.llm_client import GeminiClient, LLMClientError

        # Build the user message with prospect signals
        user_message = _build_analysis_prompt(prospect_data)

        async with GeminiClient() as gemini:
            result = await gemini.complete_json(
                system=INTENT_SYSTEM_PROMPT,
                user_message=user_message,
            )

        # Validate and build ProspectIntent from Gemini's response
        intent = ProspectIntent(
            prospect_id=prospect_id,
            service_area=result.get("service_area"),
            pain_points=result.get("pain_points", []),
            confidence=min(1.0, max(0.0, float(result.get("confidence", 0.5)))),
            urgency_level=result.get("urgency_level"),
            decision_stage=result.get("decision_stage"),
            key_questions=result.get("key_questions", []),
            analysis_source="gemini",
        )

        logger.info(
            "Gemini intent analysis succeeded",
            extra={"prospect_id": prospect_id},
        )
        return intent

    except LLMClientError as e:
        logger.warning(
            f"Gemini intent analysis failed, falling back to rules: {e}",
            extra={"prospect_id": prospect_id, "provider": e.provider},
        )
        return None
    except Exception as e:
        logger.warning(
            f"Unexpected error in Gemini analysis, falling back to rules: {e}",
            extra={"prospect_id": prospect_id},
        )
        return None


def _build_analysis_prompt(prospect_data: dict[str, Any]) -> str:
    # Assemble prospect signals into a structured prompt for Gemini.

    parts = ["Analyze this B2B prospect and determine their intent:\n"]

    # Firmographics
    if prospect_data.get("company_name"):
        parts.append(f"Company: {prospect_data['company_name']}")
    if prospect_data.get("industry"):
        parts.append(f"Industry: {prospect_data['industry']}")
    if prospect_data.get("employee_count"):
        parts.append(f"Company Size: {prospect_data['employee_count']}")

    # Contact info
    if prospect_data.get("contact_name"):
        parts.append(f"Contact: {prospect_data['contact_name']}")
    if prospect_data.get("job_title"):
        parts.append(f"Title: {prospect_data['job_title']}")

    # RTR signals
    if prospect_data.get("current_room"):
        parts.append(f"Current Room: {prospect_data['current_room']}")
    if prospect_data.get("lead_score") is not None:
        parts.append(f"Lead Score: {prospect_data['lead_score']}")
    if prospect_data.get("days_in_room"):
        parts.append(f"Days in Room: {prospect_data['days_in_room']}")
    if prospect_data.get("email_sequence_position"):
        parts.append(f"Email Sequence Position: {prospect_data['email_sequence_position']}")

    # Engagement data
    if prospect_data.get("engagement_data"):
        parts.append(f"Recent Page Visits: {prospect_data['engagement_data']}")

    return "\n".join(parts)

# =============================================================================
# Rule-Based Analysis (fallback)
# =============================================================================

def _analyze_with_rules(
    prospect_id: int,
    prospect_data: dict[str, Any],
) -> ProspectIntent:
    """Rule-based intent extraction — used when Claude is unavailable."""

    logger.info(
        "Using rule-based intent analysis",
        extra={"prospect_id": prospect_id},
    )

    current_room = prospect_data.get("current_room", "problem")
    lead_score = prospect_data.get("lead_score", 0)

    # Decision stage from room
    stage_map = {
        "problem": "awareness",
        "solution": "consideration",
        "offer": "decision",
    }

    # Urgency from lead score
    if lead_score > 50:
        urgency = "high"
    elif lead_score > 25:
        urgency = "medium"
    else:
        urgency = "low"

    return ProspectIntent(
        prospect_id=prospect_id,
        service_area=_extract_service_area(prospect_data),
        pain_points=_extract_pain_points(prospect_data),
        confidence=0.75,
        urgency_level=urgency,
        decision_stage=stage_map.get(current_room, "awareness"),
        key_questions=[],
        analysis_source="rules",
    )


def _extract_service_area(prospect_data: dict[str, Any]) -> str | None:
    """Determine primary service area interest from prospect data.

    Priority:
    1. Explicit service_area on prospect
    2. Behavioral signals from engagement_data (URL patterns)
    3. Campaign service_area (from journey circle)
    4. Industry-based heuristic (last resort)
    """

    # Check if prospect data has explicit service area
    if "service_area" in prospect_data:
        return prospect_data["service_area"]

    # Check engagement_data for page visit patterns
    engagement = prospect_data.get("engagement_data", "")
    if isinstance(engagement, str) and engagement:
        engagement_lower = engagement.lower()
        if "cloud-migration" in engagement_lower or "migration" in engagement_lower:
            return "cloud-migration"
        if "ai" in engagement_lower or "gen-ai" in engagement_lower:
            return "ai-development"
        if "data" in engagement_lower or "analytics" in engagement_lower:
            return "data-analytics"
        if "modernization" in engagement_lower or "modernize" in engagement_lower:
            return "cloud-modernization"

    # Campaign service_area from journey circle (injected by fetch_prospect_data)
    campaign_sa = prospect_data.get("campaign_service_area")
    if campaign_sa:
        return campaign_sa

    # Fallback: industry-based heuristic
    industry = (prospect_data.get("industry") or "").lower()
    if "health" in industry:
        return "data-analytics"
    elif "finance" in industry or "banking" in industry:
        return "cloud-migration"
    else:
        return "ai-development"


def _extract_pain_points(prospect_data: dict[str, Any]) -> list[str]:
    """Extract pain points from prospect signals (industry-based mapping)."""

    industry = (prospect_data.get("industry") or "").lower()

    if "health" in industry:
        return [
            "Data silos preventing analytics adoption",
            "Compliance concerns with cloud migration",
        ]
    elif "finance" in industry or "banking" in industry:
        return [
            "Legacy systems limiting innovation",
            "High maintenance costs for on-premise infrastructure",
        ]
    elif "manufacturing" in industry:
        return [
            "Operational drift causing margin pressure",
            "Difficulty scaling with current systems",
        ]
    else:
        return [
            "AI experiments stuck in POC phase",
            "Unclear roadmap for modernization",
        ]
