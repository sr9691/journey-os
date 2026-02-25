# =============================================================================
# Asset Ranker Agent
# =============================================================================
#
# Ranks available content links for a prospect based on weighted scoring:
# - Room match (required - must match prospect's current room)
# - Service area alignment (+25 points)
# - Persona match (+20 points)
# - Industry relevance (+20 points)
# - Format preference (+10 points)
# - Content freshness (+5 points)
#
# MVP: Returns mock ranked assets for testing graph flow.
# Production: Fetches real content links from WordPress via REST API
# and applies weighted scoring against prospect intent.
# =============================================================================

import logging
from typing import Any

from models.state import AgentState, ProspectIntent, RankedAsset

# Scoring weights for weighted content ranking
# Used when scoring real assets from WordPress (production)
SCORING_WEIGHTS = {
    "service_area": 25,
    "persona": 20,
    "industry": 20,
    "format_preference": 10,
    "freshness": 5,
}

logger = logging.getLogger(__name__)


def rank_assets(state: AgentState) -> dict[str, Any]:
    # Rank available content assets for the prospect
    #
    # Reads: intent_profile, prospect_data
    # Returns: ranked_assets, selected_content
    #
    # MVP: mock ranked assets based on service area
    # Production: query WordPress for real content links and score them

    intent_profile = state.get("intent_profile")
    prospect_data = state.get("prospect_data", {})

    if intent_profile is None:
        logger.warning("No intent profile available for ranking")
        return {"ranked_assets": [], "selected_content": None}

    # Handle both Pydantic model and dict (for backwards compat)
    if isinstance(intent_profile, ProspectIntent):
        service_area = intent_profile.service_area or "general"
        prospect_id = intent_profile.prospect_id
    else:
        service_area = intent_profile.get("service_area", "general")
        prospect_id = intent_profile.get("prospect_id", 0)

    logger.info(
        "Ranking assets",
        extra={
            "prospect_id": prospect_id,
            "service_area": service_area,
        },
    )

    # MVP: Return mock ranked assets based on service area
    # TODO: Replace with WordPress API call to fetch real content links
    # and apply weighted scoring per SCORING_WEIGHTS
    ranked_assets = _get_mock_assets(service_area, prospect_data)

    # Select top asset for email
    selected = ranked_assets[0] if ranked_assets else None

    logger.info(
        "Asset ranking complete",
        extra={
            "total_candidates": len(ranked_assets),
            "selected_asset": selected.title if selected else None,
        },
    )

    return {
        "ranked_assets": ranked_assets,
        "selected_content": selected,
    }


def _get_mock_assets(
    service_area: str,
    prospect_data: dict[str, Any],
) -> list[RankedAsset]:
    # Generate mock ranked assets for testing
    #
    # Production: Query rtr_room_content_links via WordPressClient,
    # then score each asset against prospect intent using SCORING_WEIGHTS.
    #
    # Content titles are from the CleanSlate article charts
    # (see CleanSlate_Article_Charts.pdf in project docs)

    mock_library: dict[str, list[RankedAsset]] = {
        "ai-development": [
            RankedAsset(
                asset_id=101,
                url="https://example.com/blog/poc-limbo",
                title="Are Your Gen AI Experiments Stuck in POC Limbo?",
                room="problem",
                score=85.0,
                match_reasons=["service_area", "pain_point_match"],
            ),
            RankedAsset(
                asset_id=102,
                url="https://example.com/blog/ai-roadmap",
                title="Building an AI Roadmap: 5 Priorities for Getting Started",
                room="solution",
                score=72.0,
                match_reasons=["service_area", "industry_match"],
            ),
        ],
        "cloud-migration": [
            RankedAsset(
                asset_id=201,
                url="https://example.com/blog/data-center-budget",
                title="Is Your Data Center Draining Your Budget?",
                room="problem",
                score=88.0,
                match_reasons=["service_area", "pain_point_match", "persona"],
            ),
            RankedAsset(
                asset_id=202,
                url="https://example.com/blog/migration-roadmap",
                title="Understanding Your Migration Roadmap and TCO",
                room="solution",
                score=70.0,
                match_reasons=["service_area"],
            ),
        ],
        "data-analytics": [
            RankedAsset(
                asset_id=301,
                url="https://example.com/blog/data-silos",
                title="Drowning in Data Silos? 7 Red Flags to Watch For",
                room="problem",
                score=82.0,
                match_reasons=["service_area", "industry_match"],
            ),
            RankedAsset(
                asset_id=302,
                url="https://example.com/blog/lakehouse-comparison",
                title="Data Lakehouse vs. Traditional Warehousing: Pros and Cons",
                room="solution",
                score=68.0,
                match_reasons=["service_area"],
            ),
        ],
        "cloud-modernization": [
            RankedAsset(
                asset_id=401,
                url="https://example.com/blog/lift-shift-fatigue",
                title="Lift and Shift Fatigue: Why Applications Aren't Truly Modern",
                room="problem",
                score=80.0,
                match_reasons=["service_area"],
            ),
            RankedAsset(
                asset_id=402,
                url="https://example.com/blog/monolith-to-microservices",
                title="Transforming Monolithic Apps to Microservices: Steps and Benefits",
                room="solution",
                score=65.0,
                match_reasons=["service_area"],
            ),
        ],
    }

    # Return assets for the service area, or default set
    return mock_library.get(service_area, mock_library["ai-development"])