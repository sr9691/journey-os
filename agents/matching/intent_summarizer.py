# =============================================================================
# Lead Intent Summarizer Agent
# =============================================================================
#
# Analyzes prospect data to extract intent signals:
# - Service area interest based on page visits and engagement
# - Pain points from engagement patterns and firmographics
# - Confidence score for recommendation quality
#
# MVP: Returns rule-based intent for testing graph flow.
# Production: Will call Claude API for deeper analysis.
# =============================================================================

import logging
from typing import Any

from models.state import AgentState, ProspectIntent

logger = logging.getLogger(__name__)


def analyze_intent(state: AgentState) -> dict[str, Any]:
    # Analyze prospect data to determine intent signals
    #
    # Reads: prospect_id, prospect_data
    # Returns: intent_profile
    #
    # MVP: rule-based extraction from prospect fields
    # Production: Claude API call for deep analysis

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

    # Build intent profile using rule-based extraction
    # TODO: Replace with Claude API call for real analysis
    intent_profile = ProspectIntent(
        prospect_id=prospect_id,
        service_area=_extract_service_area(prospect_data),
        pain_points=_extract_pain_points(prospect_data),
        confidence=0.75,
    )

    logger.info(
        "Intent analysis complete",
        extra={
            "prospect_id": prospect_id,
            "service_area": intent_profile.service_area,
            "pain_point_count": len(intent_profile.pain_points),
            "confidence": intent_profile.confidence,
        },
    )

    return {"intent_profile": intent_profile}


def _extract_service_area(prospect_data: dict[str, Any]) -> str | None:
    # Determine primary service area interest from prospect data
    #
    # Checks engagement_data (JSON of recent page visits) for URL patterns
    # that map to service areas. Falls back to industry-based heuristics.

    # Check if prospect data has explicit service area
    if "service_area" in prospect_data:
        return prospect_data["service_area"]

    # Check engagement_data for page visit patterns
    engagement = prospect_data.get("engagement_data", "")
    if isinstance(engagement, str) and engagement:
        # Look for URL patterns in engagement data
        engagement_lower = engagement.lower()
        if "cloud-migration" in engagement_lower or "migration" in engagement_lower:
            return "cloud-migration"
        if "ai" in engagement_lower or "gen-ai" in engagement_lower:
            return "ai-development"
        if "data" in engagement_lower or "analytics" in engagement_lower:
            return "data-analytics"
        if "modernization" in engagement_lower or "modernize" in engagement_lower:
            return "cloud-modernization"

    # Fallback: industry-based heuristic
    industry = prospect_data.get("industry", "").lower()
    if "health" in industry:
        return "data-analytics"
    elif "finance" in industry or "banking" in industry:
        return "cloud-migration"
    else:
        return "ai-development"


def _extract_pain_points(prospect_data: dict[str, Any]) -> list[str]:
    # Extract pain points from prospect signals
    #
    # MVP: Industry-based pain point mapping
    # Production: Analyze content engagement, form responses, behavior

    industry = prospect_data.get("industry", "").lower()

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