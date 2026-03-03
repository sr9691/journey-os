# =============================================================================
# Asset Ranker Agent
# =============================================================================
#
# Ranks available content links for a prospect based on weighted scoring:
# - Room match (required filter - assets must match prospect's current room)
# - Service area alignment (+25 points via url_summary keyword matching)
# - Persona match (+20 points via job_title to content keyword matching)
# - Industry relevance (+20 points via industry to url_summary matching)
# - Format preference (+10 points based on content type heuristic)
# - Content freshness (+5 points based on created_at recency)
#
# Fetches real content links from WordPress via REST API.
# Falls back to mock data if WordPress is unreachable.
# =============================================================================

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from models.state import AgentState, ProspectIntent, RankedAsset
from config.guardrails import get_room_from_score

logger = logging.getLogger(__name__)

# Scoring weights for content ranking
SCORING_WEIGHTS = {
    "service_area": 25,
    "persona": 20,
    "industry": 20,
    "format_preference": 10,
    "freshness": 5,
}

# Base score for room-matched assets
BASE_ROOM_MATCH_SCORE = 20

# Minimum score to include in results
MIN_SCORE_THRESHOLD = 10

# Maximum ranked assets to return
MAX_RANKED_ASSETS = 10

# Freshness: content newer than this gets full freshness points
FRESHNESS_DAYS = 90

# Persona keyword mapping: job title keywords -> persona category
PERSONA_KEYWORDS: dict[str, list[str]] = {
    "executive": ["ceo", "cto", "cio", "cfo", "coo", "chief", "president", "vp",
                   "vice president", "partner", "founder", "owner"],
    "director": ["director", "head of", "senior manager", "principal"],
    "manager": ["manager", "lead", "supervisor", "coordinator"],
    "technical": ["engineer", "developer", "architect", "analyst", "admin",
                  "devops", "sre", "data scientist"],
}

# Service area keywords for matching against url_summary/link_title
SERVICE_AREA_KEYWORDS: dict[str, list[str]] = {
    "ai-development": ["ai", "artificial intelligence", "machine learning", "gen ai",
                        "generative ai", "poc", "proof of concept", "llm", "ml"],
    "cloud-migration": ["migration", "cloud migration", "data center", "legacy",
                         "lift and shift", "aws", "azure", "7r", "tco"],
    "data-analytics": ["data", "analytics", "lakehouse", "warehouse", "data silo",
                        "real-time analytics", "data maturity", "bi"],
    "cloud-modernization": ["modernization", "modernize", "microservices",
                             "monolithic", "devops", "containerization", "kubernetes"],
}


# =============================================================================
# Main Entry Point
# =============================================================================

def rank_assets(state: AgentState) -> dict[str, Any]:
    # Rank available content assets for the prospect
    #
    # Reads: intent_profile, prospect_data, campaign_id
    # Returns: ranked_assets, selected_content
    #
    # Content selection is PROGRESSION-BASED:
    #   - If prospect has visited Problem N content → select Solution N
    #   - If prospect has visited Solution N content → select Offer N
    #   - If no content visits found → start with Problem 1 (link_order=1)
    #   - link_order pairs content across rooms (Problem 1 → Solution 1 → Offer 1)
    #
    # Falls back to room-filtered scoring if WordPress is unavailable.

    intent_profile = state.get("intent_profile")
    prospect_data = state.get("prospect_data", {})
    campaign_id = state.get("campaign_id", 0)

    if intent_profile is None:
        logger.warning("No intent profile available for ranking")
        return {"ranked_assets": [], "selected_content": None}

    # Handle both Pydantic model and dict
    if isinstance(intent_profile, ProspectIntent):
        service_area = intent_profile.service_area or "general"
        prospect_id = intent_profile.prospect_id
    else:
        service_area = intent_profile.get("service_area", "general")
        prospect_id = intent_profile.get("prospect_id", 0)

    # Determine prospect's room (used only for fallback and logging)
    room = prospect_data.get("current_room", "")
    if not room:
        lead_score = prospect_data.get("lead_score", 0)
        room = get_room_from_score(lead_score)

    # Parse urls_sent for deduplication
    urls_sent = _parse_urls_sent(prospect_data.get("urls_sent"))

    # Parse visited URLs from engagement_data
    visited_urls = _parse_visited_urls(prospect_data)

    logger.info(
        "Ranking assets",
        extra={
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "service_area": service_area,
            "room": room,
            "urls_sent_count": len(urls_sent),
            "visited_urls_count": len(visited_urls),
        },
    )

    # Try fetching ALL content links from WordPress (all rooms)
    all_content_links = _fetch_all_content_links(campaign_id)

    if all_content_links is not None:
        # Progression-based selection
        ranked_assets = _select_by_progression(
            all_links=all_content_links,
            visited_urls=visited_urls,
            urls_sent=urls_sent,
            service_area=service_area,
            prospect_data=prospect_data,
        )
    else:
        # Fallback: room-filtered scoring with mock data
        logger.info("Using mock assets (WordPress unavailable)")
        ranked_assets = _get_mock_assets(service_area, prospect_data)

    # Select top asset for email
    selected = ranked_assets[0] if ranked_assets else None

    logger.info(
        "Asset ranking complete",
        extra={
            "total_candidates": len(ranked_assets),
            "selected_asset": selected.title if selected else None,
            "selected_room": selected.room if selected else None,
            "source": "wordpress" if all_content_links is not None else "mock",
        },
    )

    return {
        "ranked_assets": ranked_assets,
        "selected_content": selected,
    }


# =============================================================================
# WordPress Fetch
# =============================================================================

def _fetch_all_content_links(
    campaign_id: int,
) -> dict[str, list[dict[str, Any]]] | None:
    # Fetch ALL content links from WordPress for the campaign (all rooms)
    # Returns dict keyed by room: {"problem": [...], "solution": [...], "offer": [...]}
    # Returns None if WordPress is unavailable (triggers mock fallback)

    from config.settings import settings

    if not settings.has_wordpress_auth:
        logger.info("No WordPress auth configured, skipping content link fetch")
        return None

    if not campaign_id:
        logger.warning("No campaign_id provided, skipping content link fetch")
        return None

    try:
        import asyncio
        from services.wordpress_client import WordPressClient

        async def _fetch() -> dict[str, list[dict[str, Any]]]:
            async with WordPressClient() as wp:
                grouped = await wp.get_content_links(campaign_id)
                return {
                    room: [link.model_dump() for link in links]
                    for room, links in grouped.items()
                }

        try:
            asyncio.get_running_loop()
            logger.warning(
                "rank_assets called from async context, cannot fetch WordPress. "
                "Consider making rank_assets async or pre-fetching content links."
            )
            return None
        except RuntimeError:
            return asyncio.run(_fetch())

    except Exception as e:
        logger.warning(
            f"Failed to fetch content links from WordPress: {e}",
            extra={"campaign_id": campaign_id},
        )
        return None


# =============================================================================
# Visited URL Parsing (delegated to content_progression)
# =============================================================================

from agents.matching.content_progression import (
    parse_visited_urls as _parse_visited_urls,
    normalize_url as _normalize_url,
    select_by_progression as _select_by_progression_impl,
)


def _select_by_progression(
    all_links: dict[str, list[dict[str, Any]]],
    visited_urls: set[str],
    urls_sent: set[str],
    service_area: str,
    prospect_data: dict[str, Any],
) -> list[RankedAsset]:
    # Wrapper that passes scoring callbacks to the progression engine

    return _select_by_progression_impl(
        all_links=all_links,
        visited_urls=visited_urls,
        urls_sent=urls_sent,
        service_area=service_area,
        prospect_data=prospect_data,
        score_fn=_score_real_assets,
        infer_content_type_fn=_infer_content_type,
    )


# =============================================================================
# Real Asset Scoring
# =============================================================================

def _score_real_assets(
    content_links: list[dict[str, Any]],
    room: str,
    service_area: str,
    prospect_data: dict[str, Any],
    urls_sent: set[str],
) -> list[RankedAsset]:
    # Score real WordPress content links using weighted criteria
    #
    # Filters:
    #   - is_active must be True
    #   - URL must not be in urls_sent
    #   - room_type must match prospect's room (already filtered by API)
    #
    # Scoring:
    #   Base room match: +20 points
    #   Service area alignment: +25 (keyword match in url_summary/link_title)
    #   Persona match: +20 (job title category match)
    #   Industry relevance: +20 (industry keywords in url_summary)
    #   Format preference: +10 (based on content type heuristic)
    #   Freshness: +5 (content newer than FRESHNESS_DAYS)

    job_title = (prospect_data.get("job_title") or "").lower()
    industry = (prospect_data.get("industry") or "").lower()

    scored: list[RankedAsset] = []

    for link in content_links:
        # Filter: inactive links
        if not link.get("is_active", True):
            continue

        # Filter: already-sent URLs
        link_url = link.get("link_url", "")
        if link_url in urls_sent:
            logger.debug(f"Skipping already-sent URL: {link_url}")
            continue

        # Score this asset
        score = BASE_ROOM_MATCH_SCORE
        match_reasons: list[str] = ["room_match"]

        # Combine searchable text from the link
        searchable = _get_searchable_text(link)

        # Service area alignment (+25)
        if _matches_service_area(searchable, service_area):
            score += SCORING_WEIGHTS["service_area"]
            match_reasons.append("service_area")

        # Persona match (+20)
        if _matches_persona(searchable, job_title):
            score += SCORING_WEIGHTS["persona"]
            match_reasons.append("persona")

        # Industry relevance (+20)
        if _matches_industry(searchable, industry):
            score += SCORING_WEIGHTS["industry"]
            match_reasons.append("industry")

        # Format preference (+10)
        if _matches_format_preference(link, prospect_data):
            score += SCORING_WEIGHTS["format_preference"]
            match_reasons.append("format_preference")

        # Freshness (+5)
        if _is_fresh(link):
            score += SCORING_WEIGHTS["freshness"]
            match_reasons.append("freshness")

        if score >= MIN_SCORE_THRESHOLD:
            scored.append(RankedAsset(
                asset_id=link.get("id", 0),
                url=link_url,
                title=link.get("link_title", ""),
                room=link.get("room_type", room),
                score=float(score),
                match_reasons=match_reasons,
                content_type=_infer_content_type(link),
                summary=link.get("url_summary") or link.get("link_description") or None,
                link_order=link.get("link_order", 0),
            ))

    # Sort by score descending, limit results
    scored.sort(key=lambda a: a.score, reverse=True)
    return scored[:MAX_RANKED_ASSETS]


# =============================================================================
# Scoring Helpers
# =============================================================================

def _get_searchable_text(link: dict[str, Any]) -> str:
    # Combine link title, url_summary, and description into searchable text
    parts = [
        link.get("link_title", ""),
        link.get("url_summary", ""),
        link.get("link_description", ""),
    ]
    return " ".join(p for p in parts if p).lower()


def _matches_service_area(searchable: str, service_area: str) -> bool:
    # Check if content aligns with the prospect's service area interest
    # Uses keyword matching against url_summary and link_title
    keywords = SERVICE_AREA_KEYWORDS.get(service_area, [])
    return any(kw in searchable for kw in keywords)


def _matches_persona(searchable: str, job_title: str) -> bool:
    # Check if content targets the prospect's persona based on job title
    # Maps job title to persona category, then checks content keywords
    if not job_title:
        return False

    prospect_persona = _get_persona_category(job_title)
    if not prospect_persona:
        return False

    # Content keywords that indicate targeting a specific persona
    persona_content_keywords: dict[str, list[str]] = {
        "executive": ["strategy", "roi", "leadership", "risk", "investment",
                       "business value", "ceo", "cto", "executive"],
        "director": ["roadmap", "planning", "team", "process", "priorities",
                      "assessment", "framework"],
        "manager": ["implementation", "workflow", "coordination", "manage",
                     "steps", "practical"],
        "technical": ["architecture", "implementation", "how to", "technical",
                       "guide", "steps", "deploy", "configure", "build"],
    }

    content_kws = persona_content_keywords.get(prospect_persona, [])
    return any(kw in searchable for kw in content_kws)


def _get_persona_category(job_title: str) -> str | None:
    # Map a job title to a persona category
    title_lower = job_title.lower()
    for category, keywords in PERSONA_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return None


def _matches_industry(searchable: str, industry: str) -> bool:
    # Check if content is relevant to the prospect's industry
    if not industry:
        return False

    # Direct industry name match
    if industry in searchable:
        return True

    # Common industry alias matching
    industry_aliases: dict[str, list[str]] = {
        "healthcare": ["health", "medical", "clinical", "hipaa", "patient"],
        "financial services": ["finance", "banking", "fintech", "compliance"],
        "manufacturing": ["manufacturing", "supply chain", "operations", "iot"],
        "technology": ["tech", "saas", "software", "platform"],
        "retail": ["retail", "ecommerce", "e-commerce", "consumer"],
    }

    for base_industry, aliases in industry_aliases.items():
        if any(alias in industry for alias in [base_industry] + aliases):
            return any(alias in searchable for alias in aliases)

    return False


def _infer_content_type(link: dict[str, Any]) -> str:
    # Infer content type from title/summary keywords
    # Since content_type isn't stored in the DB table, we heuristic it

    searchable = _get_searchable_text(link)

    if any(kw in searchable for kw in ["case study", "success story", "how we helped"]):
        return "case_study"
    if any(kw in searchable for kw in ["whitepaper", "white paper", "research report"]):
        return "whitepaper"
    if any(kw in searchable for kw in ["guide", "how to", "step by step", "steps"]):
        return "guide"
    if any(kw in searchable for kw in ["webinar", "video", "watch"]):
        return "video"
    if any(kw in searchable for kw in ["checklist", "template", "toolkit"]):
        return "tool"

    return "article"


def _matches_format_preference(
    link: dict[str, Any],
    prospect_data: dict[str, Any],
) -> bool:
    # Match content format to prospect's room stage
    # Since content_type isn't on the DB table, infer from title/summary keywords
    #
    # Problem room -> educational, awareness content
    # Solution room -> comparison, how-to content
    # Offer room -> action-oriented, ROI content

    room = prospect_data.get("current_room", "problem")
    searchable = _get_searchable_text(link)

    if room == "problem":
        return any(kw in searchable for kw in [
            "why", "symptom", "sign", "red flag", "breakdown", "hidden",
            "what you're missing", "obstacle",
        ])
    elif room == "solution":
        return any(kw in searchable for kw in [
            "how to", "vs", "versus", "pros and cons", "roadmap",
            "framework", "guide", "steps", "assessment",
        ])
    elif room == "offer":
        return any(kw in searchable for kw in [
            "practical", "production ready", "accelerate", "speed",
            "cost", "roi", "automate", "partner",
        ])

    return False


def _is_fresh(link: dict[str, Any]) -> bool:
    # Check if content was created/updated within FRESHNESS_DAYS
    date_str = link.get("updated_at") or link.get("created_at")
    if not date_str:
        return False

    try:
        created = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        cutoff = datetime.now() - timedelta(days=FRESHNESS_DAYS)
        return created >= cutoff
    except (ValueError, TypeError):
        return False


def _parse_urls_sent(urls_sent_raw: Any) -> set[str]:
    # Parse the urls_sent field from prospect data
    # WordPress stores this as a JSON array string or Python list
    if not urls_sent_raw:
        return set()

    if isinstance(urls_sent_raw, list):
        return set(urls_sent_raw)

    if isinstance(urls_sent_raw, str):
        try:
            parsed = json.loads(urls_sent_raw)
            if isinstance(parsed, list):
                return set(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

    return set()


# =============================================================================
# Mock Fallback (for testing without WordPress)
# =============================================================================

def _get_mock_assets(
    service_area: str,
    prospect_data: dict[str, Any],
) -> list[RankedAsset]:
    # Generate mock ranked assets for testing
    # Content titles from CleanSlate_Article_Charts.pdf

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
