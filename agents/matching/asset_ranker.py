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
# Phase 2: Fetches real content links from WordPress via REST API
# and applies weighted scoring against prospect intent.
# Falls back to mock assets if WordPress is unreachable.
# =============================================================================

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from config.settings import settings
from models.state import AgentState, ProspectIntent, RankedAsset

# Scoring weights for weighted content ranking
SCORING_WEIGHTS = {
    "service_area": 25,
    "persona": 20,
    "industry": 20,
    "format_preference": 10,
    "freshness": 5,
}

# Service area keyword mappings for content matching
SERVICE_AREA_KEYWORDS: dict[str, list[str]] = {
    "ai-development": [
        "ai", "artificial intelligence", "machine learning", "gen ai",
        "generative ai", "llm", "deep learning", "neural", "poc",
        "proof of concept", "ml ops", "mlops",
    ],
    "cloud-migration": [
        "cloud migration", "migrate", "data center", "on-premise",
        "on-prem", "lift and shift", "rehost", "aws", "azure", "gcp",
        "tco", "total cost",
    ],
    "data-analytics": [
        "data analytics", "data silo", "analytics", "dashboard",
        "business intelligence", "bi", "data lake", "lakehouse",
        "warehouse", "etl", "data pipeline",
    ],
    "cloud-modernization": [
        "modernization", "modernize", "microservices", "containerization",
        "kubernetes", "docker", "serverless", "refactor", "monolith",
        "legacy application",
    ],
}

# Persona-to-content-type mapping for job title alignment
PERSONA_KEYWORDS: dict[str, list[str]] = {
    # C-suite / VP — interested in strategy, ROI, business outcomes
    "executive": [
        "strategy", "roadmap", "roi", "business case", "digital transformation",
        "cost", "budget", "competitive", "board", "leadership",
    ],
    # Director / Manager — interested in implementation, team, process
    "manager": [
        "implementation", "team", "process", "project", "timeline",
        "resource", "plan", "manage", "workflow", "operational",
    ],
    # Technical / Engineer — interested in architecture, tools, how-to
    "technical": [
        "architecture", "technical", "engineer", "developer", "api",
        "infrastructure", "code", "performance", "security", "deployment",
    ],
}

# Job title patterns mapped to persona types
JOB_TITLE_PERSONA: dict[str, list[str]] = {
    "executive": [
        "ceo", "cto", "cio", "cfo", "coo", "chief", "vp", "vice president",
        "president", "founder", "owner", "partner",
    ],
    "manager": [
        "director", "manager", "head of", "lead", "supervisor", "coordinator",
    ],
    "technical": [
        "engineer", "developer", "architect", "analyst", "admin",
        "devops", "sre", "scientist", "programmer",
    ],
}

logger = logging.getLogger(__name__)


async def rank_assets(state: AgentState) -> dict[str, Any]:
    """Rank available content assets for the prospect.

    Reads: intent_profile, prospect_data, campaign_id
    Returns: ranked_assets, selected_content

    Fetches real content links from WordPress when auth is configured,
    applies weighted scoring, and falls back to mock data otherwise.
    """

    intent_profile = state.get("intent_profile")
    prospect_data = state.get("prospect_data", {})
    campaign_id = state.get("campaign_id", prospect_data.get("campaign_id", 0))

    if intent_profile is None:
        logger.warning("No intent profile available for ranking")
        return {"ranked_assets": [], "selected_content": None}

    # Normalize intent_profile access
    if isinstance(intent_profile, ProspectIntent):
        service_area = intent_profile.service_area or "general"
        prospect_id = intent_profile.prospect_id
    else:
        service_area = intent_profile.get("service_area", "general")
        prospect_id = intent_profile.get("prospect_id", 0)

    current_room = prospect_data.get("current_room", "problem")

    # Parse urls_sent — may be list, JSON string, or comma-separated
    urls_sent = prospect_data.get("urls_sent", [])
    if isinstance(urls_sent, str):
        try:
            urls_sent = json.loads(urls_sent)
        except (json.JSONDecodeError, TypeError):
            urls_sent = [u.strip() for u in urls_sent.split(",") if u.strip()]

    logger.info(
        "Ranking assets",
        extra={
            "prospect_id": prospect_id,
            "service_area": service_area,
            "room": current_room,
            "campaign_id": campaign_id,
            "urls_already_sent": len(urls_sent),
        },
    )

    # Try fetching real content links from WordPress
    ranked_assets = await _score_real_assets(
        campaign_id=campaign_id,
        current_room=current_room,
        service_area=service_area,
        prospect_data=prospect_data,
        urls_sent=urls_sent,
    )

    # Fall back to mock if no real assets returned
    if not ranked_assets:
        logger.info("No real assets scored, falling back to mock data")
        ranked_assets = _get_mock_assets(service_area, prospect_data)

    # Select top asset for email
    selected = ranked_assets[0] if ranked_assets else None

    logger.info(
        "Asset ranking complete",
        extra={
            "total_candidates": len(ranked_assets),
            "selected_asset": selected.title if selected else None,
            "selected_score": selected.score if selected else None,
        },
    )

    return {
        "ranked_assets": ranked_assets,
        "selected_content": selected,
    }


# =============================================================================
# Real Scoring (Phase 2)
# =============================================================================

async def _score_real_assets(
    campaign_id: int,
    current_room: str,
    service_area: str,
    prospect_data: dict[str, Any],
    urls_sent: list[str],
) -> list[RankedAsset]:
    """Fetch content links from WordPress and score them with weighted criteria."""

    if not settings.has_wordpress_auth:
        logger.info("No WordPress auth configured, skipping real asset fetch")
        return []

    if not campaign_id:
        logger.warning("No campaign_id provided, skipping real asset fetch")
        return []

    try:
        from services.wordpress_client import WordPressClient

        async with WordPressClient() as wp:
            # Fetch content links for the prospect's current room
            content_links = await wp.get_content_links_flat(
                campaign_id=campaign_id,
                room=current_room,
            )

        if not content_links:
            logger.info(
                "No content links found for campaign/room",
                extra={"campaign_id": campaign_id, "room": current_room},
            )
            return []

        # Filter and score
        scored: list[RankedAsset] = []

        for link in content_links:
            # Skip inactive links
            if not link.is_active:
                continue

            # Skip already-sent URLs
            if link.link_url in urls_sent:
                logger.debug(f"Skipping already-sent URL: {link.link_url}")
                continue

            score, reasons = _compute_score(
                link=link,
                service_area=service_area,
                prospect_data=prospect_data,
            )

            scored.append(RankedAsset(
                asset_id=link.id,
                url=link.link_url,
                title=link.link_title,
                room=link.room_type,
                score=score,
                match_reasons=reasons,
            ))

        # Sort descending by score
        scored.sort(key=lambda a: a.score, reverse=True)

        logger.info(
            "Scored real assets from WordPress",
            extra={
                "total_fetched": len(content_links),
                "after_filtering": len(scored),
                "top_score": scored[0].score if scored else 0,
            },
        )

        return scored

    except Exception as e:
        logger.warning(f"Real asset scoring failed, will use mock: {e}")
        return []


def _compute_score(
    link: Any,  # ContentLink from wordpress_client
    service_area: str,
    prospect_data: dict[str, Any],
) -> tuple[float, list[str]]:
    """Compute weighted relevance score for a single content link."""

    score = 0.0
    reasons: list[str] = []

    # Combine searchable text from the content link
    content_text = " ".join([
        link.link_title or "",
        link.url_summary or "",
        link.link_description or "",
    ]).lower()

    # --- Service area alignment (+25) ---
    sa_keywords = SERVICE_AREA_KEYWORDS.get(service_area, [])
    if sa_keywords and any(kw in content_text for kw in sa_keywords):
        score += SCORING_WEIGHTS["service_area"]
        reasons.append("service_area")

    # --- Persona match (+20) ---
    persona = _get_persona(prospect_data.get("job_title", ""))
    if persona:
        persona_kws = PERSONA_KEYWORDS.get(persona, [])
        if persona_kws and any(kw in content_text for kw in persona_kws):
            score += SCORING_WEIGHTS["persona"]
            reasons.append("persona")

    # --- Industry relevance (+20) ---
    industry = (prospect_data.get("industry") or "").lower()
    if industry and industry in content_text:
        score += SCORING_WEIGHTS["industry"]
        reasons.append("industry")
    elif industry:
        # Partial match — check if any significant industry word appears
        industry_words = [w for w in industry.split() if len(w) > 3]
        if industry_words and any(w in content_text for w in industry_words):
            score += SCORING_WEIGHTS["industry"] * 0.5  # Half credit
            reasons.append("industry_partial")

    # --- Format preference (+10) ---
    # Check engagement_data for content type preferences
    engagement = (prospect_data.get("engagement_data") or "").lower()
    if engagement:
        # If engagement URLs share path segments with this link, boost
        link_url_lower = (link.link_url or "").lower()
        segments = _url_segments(link_url_lower)
        if any(seg in engagement for seg in segments if len(seg) > 3):
            score += SCORING_WEIGHTS["format_preference"]
            reasons.append("format_preference")

    # --- Freshness (+5) ---
    freshness_score = _compute_freshness(link.updated_at or link.created_at)
    if freshness_score > 0:
        score += freshness_score
        reasons.append("freshness")

    # Base score: use link_order as tiebreaker (lower order = higher priority)
    order_bonus = max(0.0, 5.0 - (link.link_order * 0.5))
    score += order_bonus
    if order_bonus > 0:
        reasons.append("link_order")

    return round(score, 1), reasons


def _get_persona(job_title: str) -> str | None:
    """Map a job title to a persona category."""

    if not job_title:
        return None

    title_lower = job_title.lower()

    for persona, patterns in JOB_TITLE_PERSONA.items():
        if any(p in title_lower for p in patterns):
            return persona

    return None


def _url_segments(url: str) -> list[str]:
    """Extract meaningful path segments from a URL."""
    try:
        path = urlparse(url).path
        return [s for s in path.split("/") if s]
    except Exception:
        return []


def _compute_freshness(date_str: str | None) -> float:
    """Score content freshness: full points if <30 days, partial if <90."""

    if not date_str:
        return 0.0

    try:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        else:
            return 0.0

        age_days = (datetime.now(timezone.utc) - dt).days

        if age_days <= 30:
            return SCORING_WEIGHTS["freshness"]  # Full 5 points
        elif age_days <= 90:
            return SCORING_WEIGHTS["freshness"] * 0.5  # 2.5 points
        else:
            return 0.0

    except Exception:
        return 0.0


# =============================================================================
# Mock Data (fallback when WordPress is unreachable)
# =============================================================================

def _get_mock_assets(
    service_area: str,
    prospect_data: dict[str, Any],
) -> list[RankedAsset]:
    """Generate mock ranked assets for testing.

    Used when WordPress is unreachable or unconfigured.
    Content titles are from the CleanSlate article charts.
    """

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

    return mock_library.get(service_area, mock_library["ai-development"])
