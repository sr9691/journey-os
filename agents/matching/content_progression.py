# =============================================================================
# Content Progression Engine
# =============================================================================
#
# Selects content based on the prospect's consumption history.
# Uses link_order to pair content across rooms:
#   Problem order=1 → Solution order=1 → Offer order=1
#
# Logic:
#   - If prospect visited Problem N → select Solution N
#   - If prospect visited Solution N → select Offer N
#   - If prospect visited Offer N → sequence complete, try next order
#   - If no visits found → start with Problem 1
#
# =============================================================================

import json
import logging
from typing import Any

from models.state import RankedAsset

logger = logging.getLogger(__name__)

# Room progression order — content advances through this sequence
ROOM_PROGRESSION = ["problem", "solution", "offer"]


# =============================================================================
# Visited URL Parsing
# =============================================================================

def parse_visited_urls(prospect_data: dict[str, Any]) -> set[str]:
    # Extract URLs the prospect has actually visited from engagement_data
    # engagement_data is a JSON string from WordPress containing page visit info
    # Also checks pages_visited if provided directly

    visited: set[str] = set()

    # Direct pages_visited field (used in test data)
    pages_visited = prospect_data.get("pages_visited", [])
    if isinstance(pages_visited, list):
        for url in pages_visited:
            if isinstance(url, str) and url:
                visited.add(normalize_url(url))

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

    # Handle list of visit records or URLs
    if isinstance(engagement, list):
        for item in engagement:
            if isinstance(item, str):
                visited.add(normalize_url(item))
            elif isinstance(item, dict):
                url = item.get("url") or item.get("page_url") or item.get("path", "")
                if url:
                    visited.add(normalize_url(url))

    return visited


def normalize_url(url: str) -> str:
    # Normalize URL for comparison — strip trailing slashes, lowercase, strip protocol
    url = url.strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    if url.startswith("www."):
        url = url[4:]
    return url


# =============================================================================
# Progression-Based Content Selection
# =============================================================================

def select_by_progression(
    all_links: dict[str, list[dict[str, Any]]],
    visited_urls: set[str],
    urls_sent: set[str],
    service_area: str,
    prospect_data: dict[str, Any],
    score_fn: Any = None,
    infer_content_type_fn: Any = None,
) -> list[RankedAsset]:
    # Select content based on the prospect's consumption progression
    #
    # score_fn: callback to _score_real_assets for alternative scoring
    # infer_content_type_fn: callback to _infer_content_type

    # Step 1: Index all active links by link_order and room
    order_map: dict[int, dict[str, dict[str, Any]]] = {}

    for room in ROOM_PROGRESSION:
        for link in all_links.get(room, []):
            if not link.get("is_active", True):
                continue
            order = link.get("link_order", 0)
            if order not in order_map:
                order_map[order] = {}
            order_map[order][room] = link

    if not order_map:
        logger.warning("No active content links found in any room")
        return []

    sorted_orders = sorted(order_map.keys())

    logger.debug(
        "Content progression map",
        extra={
            "orders": sorted_orders,
            "rooms_per_order": {
                o: list(order_map[o].keys()) for o in sorted_orders
            },
        },
    )

    # Step 2: Find the best next content based on visit history
    next_content = _find_next_content(
        order_map=order_map,
        sorted_orders=sorted_orders,
        visited_urls=visited_urls,
        urls_sent=urls_sent,
    )

    if not next_content:
        logger.info("All content sequences complete or sent, falling back to scoring")
        return _score_unsent(all_links, urls_sent, service_area, prospect_data, score_fn)

    # Step 3: Build ranked list with the progression pick first
    primary = _link_to_ranked_asset(
        next_content["link"], next_content["reason"], infer_content_type_fn,
    )

    # Score remaining unsent content as alternatives
    alternatives = _score_unsent(
        all_links, urls_sent | {normalize_url(primary.url)},
        service_area, prospect_data, score_fn,
    )

    return [primary] + alternatives


def _find_next_content(
    order_map: dict[int, dict[str, dict[str, Any]]],
    sorted_orders: list[int],
    visited_urls: set[str],
    urls_sent: set[str],
) -> dict[str, Any] | None:
    # Walk through link_orders and find the next content to send
    #
    # For each link_order, check if the prospect has visited content in any room.
    # If they visited the Problem content → return the Solution content.
    # If they visited the Solution content → return the Offer content.
    # If they visited the Offer content → that sequence is done, try next order.
    #
    # If NO visits found across all orders → return Problem at the lowest order.

    has_any_visit = False

    for order in sorted_orders:
        rooms = order_map[order]

        # Check which rooms the prospect has visited at this link_order
        furthest_visited_room = None
        for room in ROOM_PROGRESSION:
            link = rooms.get(room)
            if not link:
                continue
            link_url_normalized = normalize_url(link.get("link_url", ""))
            if link_url_normalized and link_url_normalized in visited_urls:
                furthest_visited_room = room
                has_any_visit = True

        if furthest_visited_room:
            # Prospect has visited content at this order — advance to next room
            current_idx = ROOM_PROGRESSION.index(furthest_visited_room)
            next_idx = current_idx + 1

            if next_idx < len(ROOM_PROGRESSION):
                next_room = ROOM_PROGRESSION[next_idx]
                next_link = rooms.get(next_room)

                if next_link:
                    next_url = next_link.get("link_url", "")
                    # Don't pick something already sent
                    if next_url and next_url not in urls_sent:
                        logger.info(
                            f"Progression: visited {furthest_visited_room} order={order} "
                            f"→ advancing to {next_room} order={order}",
                        )
                        return {
                            "link": next_link,
                            "reason": (
                                f"progression_{furthest_visited_room}_to_{next_room}"
                            ),
                        }
                    else:
                        logger.debug(
                            f"Next content at order={order} room={next_room} already sent"
                        )
            else:
                # Visited the Offer — this sequence is fully complete
                logger.debug(f"Sequence complete at order={order}")
                continue

    # No visits found in any content — start with Problem at lowest order
    if not has_any_visit:
        for order in sorted_orders:
            problem_link = order_map[order].get("problem")
            if problem_link:
                problem_url = problem_link.get("link_url", "")
                if problem_url and problem_url not in urls_sent:
                    logger.info(
                        f"No content visits found → starting with problem order={order}"
                    )
                    return {
                        "link": problem_link,
                        "reason": "first_touch_problem",
                    }

    return None


def _link_to_ranked_asset(
    link: dict[str, Any],
    reason: str,
    infer_content_type_fn: Any = None,
) -> RankedAsset:
    # Convert a content link dict to a RankedAsset with a progression reason

    content_type = "article"
    if infer_content_type_fn:
        content_type = infer_content_type_fn(link)

    return RankedAsset(
        asset_id=link.get("id", 0),
        url=link.get("link_url", ""),
        title=link.get("link_title", ""),
        room=link.get("room_type", ""),
        score=100.0,  # Progression pick always ranks highest
        match_reasons=[reason],
        content_type=content_type,
        summary=link.get("url_summary") or link.get("link_description") or None,
        link_order=link.get("link_order", 0),
    )


def _score_unsent(
    all_links: dict[str, list[dict[str, Any]]],
    urls_sent: set[str],
    service_area: str,
    prospect_data: dict[str, Any],
    score_fn: Any = None,
) -> list[RankedAsset]:
    # Score all unsent content across rooms as alternatives

    if not score_fn:
        return []

    flat_links = []
    for room_links in all_links.values():
        flat_links.extend(room_links)

    return score_fn(
        content_links=flat_links,
        room="all",
        service_area=service_area,
        prospect_data=prospect_data,
        urls_sent=urls_sent,
    )
