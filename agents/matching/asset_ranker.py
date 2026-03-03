# =============================================================================
# Asset Ranker Agent
# =============================================================================
#
# Selects the next content link for a prospect based on:
#   1. Room gate — prospect's room (from lead_score) is the default
#   2. Visit-based unlock — if prospect visited content at a link_order,
#      the next room's content at that same order is unlocked
#      (Problem visited -> Solution unlocked -> Offer unlocked)
#   3. link_order ascending — lowest unsent order wins
#
# No mocks, no fallbacks. Errors propagate if:
#   - WordPress is unavailable
#   - Campaign has no active content for the relevant room
#   - All content for the prospect is exhausted
# =============================================================================

import json
import logging
from typing import Any

from models.state import AgentState, ProspectIntent, RankedAsset
from config.guardrails import get_room_from_score

logger = logging.getLogger(__name__)

# Room progression order
ROOM_PROGRESSION = ["problem", "solution", "offer"]


# =============================================================================
# Main Entry Point
# =============================================================================

async def rank_assets(state: AgentState) -> dict[str, Any]:
    # Select the next content link for the prospect
    #
    # Reads: intent_profile, prospect_data, campaign_id
    # Returns: ranked_assets (list with single selection), selected_content
    #
    # Room is a hard gate with visit-based unlock:
    #   - Default: content must match prospect's current room
    #   - Exception: if prospect VISITED content at link_order N,
    #     the next room's content at order N is unlocked
    #   - Chain: Problem visited -> Solution unlocked,
    #            Solution visited -> Offer unlocked
    #
    # Within eligible content, lowest unsent link_order wins.
    # Errors if no content is available (no mocks, no fallbacks).

    intent_profile = state.get("intent_profile")
    prospect_data = state.get("prospect_data", {})
    campaign_id = state.get("campaign_id", 0)
    prospect_id = state.get("prospect_id", 0)

    if intent_profile is None:
        logger.error("No intent profile available for ranking")
        return {
            "ranked_assets": [],
            "selected_content": None,
            "error": "Missing intent_profile in state",
        }

    # Determine prospect's room
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
            "room": room,
            "urls_sent_count": len(urls_sent),
            "visited_urls_count": len(visited_urls),
        },
    )

    # Fetch ALL content links from WordPress (all rooms needed for progression check)
    all_links = await _fetch_all_content_links(campaign_id)

    # Select content using room-gated progression
    selected = _select_content(
        all_links=all_links,
        prospect_room=room,
        visited_urls=visited_urls,
        urls_sent=urls_sent,
        prospect_id=prospect_id,
        campaign_id=campaign_id,
    )

    logger.info(
        "Asset ranking complete",
        extra={
            "prospect_id": prospect_id,
            "selected_title": selected.title,
            "selected_room": selected.room,
            "selected_order": selected.link_order,
            "match_reason": selected.match_reasons[0] if selected.match_reasons else "",
        },
    )

    return {
        "ranked_assets": [selected],
        "selected_content": selected,
    }


# =============================================================================
# Content Selection (room-gated with visit-based unlock)
# =============================================================================

def _select_content(
    all_links: dict[str, list[dict[str, Any]]],
    prospect_room: str,
    visited_urls: set[str],
    urls_sent: set[str],
    prospect_id: int,
    campaign_id: int,
) -> RankedAsset:
    # Select the next content link using room-gated progression
    #
    # For each link_order (ascending):
    #   1. Check if prospect visited content at earlier rooms in the chain
    #   2. Determine the highest unlocked room at this order
    #   3. If that content hasn't been sent, select it
    #
    # Raises ValueError if no content is available.

    # Index all active links by (link_order, room)
    order_map: dict[int, dict[str, dict[str, Any]]] = {}

    for room_key in ROOM_PROGRESSION:
        for link in all_links.get(room_key, []):
            if not link.get("is_active", True):
                continue
            order = link.get("link_order", 0)
            if order not in order_map:
                order_map[order] = {}
            order_map[order][room_key] = link

    if not order_map:
        raise ValueError(
            f"No active content links for campaign {campaign_id}. "
            f"Content team needs to add content."
        )

    sorted_orders = sorted(order_map.keys())

    # Check if ANY content exists for the prospect's room (or unlockable rooms)
    has_any_room_content = False

    for order in sorted_orders:
        rooms_at_order = order_map[order]

        # Determine the target room at this link_order
        target_room = _get_target_room(
            rooms_at_order=rooms_at_order,
            prospect_room=prospect_room,
            visited_urls=visited_urls,
        )

        if target_room is None:
            continue

        has_any_room_content = True
        target_link = rooms_at_order.get(target_room)

        if target_link is None:
            continue

        target_url = target_link.get("link_url", "")

        # Skip if already sent
        if target_url and _normalize_url(target_url) in urls_sent:
            logger.debug(
                f"Skipping already-sent content: order={order} room={target_room}"
            )
            continue

        # Found an unsent candidate
        logger.info(
            f"Selected content: order={order} room={target_room}",
            extra={
                "prospect_id": prospect_id,
                "link_order": order,
                "target_room": target_room,
                "prospect_room": prospect_room,
            },
        )

        reason = (
            "room_match"
            if target_room == prospect_room
            else f"progression_unlock_{target_room}"
        )

        return _link_to_ranked_asset(target_link, reason)

    # No unsent candidate found
    if not has_any_room_content:
        raise ValueError(
            f"Campaign {campaign_id} has no content for room '{prospect_room}' "
            f"(or unlockable rooms). Campaign may be misconfigured."
        )

    raise ValueError(
        f"All content exhausted for prospect {prospect_id} in room "
        f"'{prospect_room}'. Content team needs to add more content."
    )


def _get_target_room(
    rooms_at_order: dict[str, dict[str, Any]],
    prospect_room: str,
    visited_urls: set[str],
) -> str | None:
    # Determine the target room for a given link_order
    #
    # Logic:
    #   - Start from the prospect's room
    #   - If prospect visited content at current room, unlock next room
    #   - Chain forward until we find unvisited content or hit the end
    #   - Never go BELOW the prospect's room
    #
    # Returns the room to send content from, or None if sequence is complete.

    prospect_room_idx = (
        ROOM_PROGRESSION.index(prospect_room)
        if prospect_room in ROOM_PROGRESSION
        else 0
    )

    # Start at the prospect's room and check for visit-based unlocks
    target_idx = prospect_room_idx

    while target_idx < len(ROOM_PROGRESSION):
        current_room = ROOM_PROGRESSION[target_idx]
        link = rooms_at_order.get(current_room)

        if link is None:
            # No content at this room for this order — can't progress further
            break

        link_url = link.get("link_url", "")
        if link_url and _normalize_url(link_url) in visited_urls:
            # Prospect visited this content — unlock next room
            target_idx += 1
            continue

        # Prospect hasn't visited this content — this is the target
        return current_room

    # Walked past the end (all visited) or no content — sequence complete
    return None


# =============================================================================
# WordPress Fetch
# =============================================================================

async def _fetch_all_content_links(
    campaign_id: int,
) -> dict[str, list[dict[str, Any]]]:
    # Fetch ALL content links from WordPress for the campaign (all rooms)
    # Returns dict keyed by room: {"problem": [...], "solution": [...], "offer": [...]}
    # Raises ValueError if WordPress is unavailable or campaign has no content

    from config.settings import settings

    if not settings.has_wordpress_auth:
        raise ValueError(
            "WordPress auth not configured. "
            "Set WORDPRESS_APP_USER and WORDPRESS_APP_PASSWORD in .env"
        )

    if not campaign_id:
        raise ValueError("No campaign_id provided")

    try:
        from services.wordpress_client import WordPressClient

        async with WordPressClient() as wp:
            grouped = await wp.get_content_links(campaign_id)
            return {
                room: [link.model_dump() for link in links]
                for room, links in grouped.items()
            }

    except Exception as e:
        raise ValueError(
            f"Failed to fetch content links for campaign {campaign_id}: {e}"
        ) from e


# =============================================================================
# Helpers
# =============================================================================

def _link_to_ranked_asset(
    link: dict[str, Any],
    reason: str,
) -> RankedAsset:
    # Convert a content link dict to a RankedAsset

    return RankedAsset(
        asset_id=link.get("id", 0),
        url=link.get("link_url", ""),
        title=link.get("link_title", ""),
        room=link.get("room_type", ""),
        score=100.0,
        match_reasons=[reason],
        content_type="article",
        summary=link.get("url_summary") or link.get("link_description") or None,
        link_order=link.get("link_order", 0),
    )


def _normalize_url(url: str) -> str:
    # Normalize URL for comparison
    url = url.strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    if url.startswith("www."):
        url = url[4:]
    return url


def _parse_visited_urls(prospect_data: dict[str, Any]) -> set[str]:
    # Extract URLs the prospect has visited from engagement_data and pages_visited

    visited: set[str] = set()

    # Direct pages_visited field
    pages_visited = prospect_data.get("pages_visited", [])
    if isinstance(pages_visited, list):
        for url in pages_visited:
            if isinstance(url, str) and url:
                visited.add(_normalize_url(url))

    # Parse engagement_data JSON string
    engagement_raw = prospect_data.get("engagement_data")
    if not engagement_raw:
        return visited

    if isinstance(engagement_raw, str):
        try:
            engagement = json.loads(engagement_raw)
        except (json.JSONDecodeError, TypeError):
            return visited
    elif isinstance(engagement_raw, (list, dict)):
        engagement = engagement_raw
    else:
        return visited

    if isinstance(engagement, list):
        for item in engagement:
            if isinstance(item, str):
                visited.add(_normalize_url(item))
            elif isinstance(item, dict):
                url = item.get("url") or item.get("page_url") or item.get("path", "")
                if url:
                    visited.add(_normalize_url(url))

    return visited


def _parse_urls_sent(urls_sent_raw: Any) -> set[str]:
    # Parse the urls_sent field from prospect data
    if not urls_sent_raw:
        return set()

    if isinstance(urls_sent_raw, list):
        return {_normalize_url(u) for u in urls_sent_raw if isinstance(u, str)}

    if isinstance(urls_sent_raw, str):
        try:
            parsed = json.loads(urls_sent_raw)
            if isinstance(parsed, list):
                return {_normalize_url(u) for u in parsed if isinstance(u, str)}
        except (json.JSONDecodeError, TypeError):
            pass

    return set()
