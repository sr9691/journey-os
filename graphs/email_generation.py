# =============================================================================
# Email Generation Workflow Graph
# =============================================================================
#
# A LangGraph workflow that orchestrates the content recommendation
# and email generation process for DirectReach prospects.
#
# Flow:
# 1. fetch_prospect_data - Fetch real prospect data from WordPress (or mock)
# 2. analyze_intent - Extract intent signals from prospect data
# 3. rank_assets - Score and rank content for the prospect
# 4. compose_email - Generate personalized email with Gemini (or template)
# 5. inspect_guardrails - Check content against room-specific rules
#
# Phase 1: Added real WordPress data fetching with fallback to mock.
# Phase 2: rank_assets now fetches real content links from WordPress
#           and applies weighted scoring. Falls back to mock data.
# Phase 4: Added guardrail inspector node to validate content against
#           room-specific RTR rules.
# Phase 5: Added email composer node using Gemini API with template
#           fallback. Generates room-appropriate outreach emails.
# =============================================================================

import logging
from typing import Any, Literal

from langgraph.graph import StateGraph, END

from config.settings import settings
from models.state import AgentState
from agents.matching.intent_summarizer import analyze_intent
from agents.matching.asset_ranker import rank_assets
from agents.email.compose_field_note import compose_email_v2
from agents.quality.guardrail_inspector import inspect_guardrails
from agents.quality.revision_interpreter import interpret_revisions, MAX_REVISION_ATTEMPTS

logger = logging.getLogger(__name__)


# =============================================================================
# Graph Nodes
# =============================================================================

async def fetch_prospect_data(state: AgentState) -> dict[str, Any]:
    # Fetch prospect data from WordPress REST API
    # Errors if WordPress is unreachable or unconfigured (no mock fallback)
    #
    # Requires WORDPRESS_APP_USER and WORDPRESS_APP_PASSWORD in .env
    # for Basic Auth against endpoints using current_user_can()

    prospect_id = state["prospect_id"]
    campaign_id = state["campaign_id"]

    # If prospect_data was already provided (e.g. by test), skip fetch
    if state.get("prospect_data") is not None:
        logger.info(
            "Using pre-provided prospect data",
            extra={"prospect_id": prospect_id},
        )
        return {"current_step": "fetch_prospect_data"}

    # Validate WordPress auth
    if not settings.has_wordpress_auth:
        return {
            "error": "WordPress auth not configured. "
                     "Set WORDPRESS_APP_USER and WORDPRESS_APP_PASSWORD in .env",
            "current_step": "fetch_prospect_data",
        }

    try:
        from services.wordpress_client import WordPressClient

        async with WordPressClient() as wp:
            prospect = await wp.get_prospect(prospect_id)

            # Also fetch campaign to get service_area from journey circle
            campaign_service_area = None
            if campaign_id:
                try:
                    campaign = await wp.get_campaign(campaign_id)
                    campaign_service_area = campaign.service_area
                except Exception as ce:
                    logger.warning(
                        f"Failed to fetch campaign {campaign_id}: {ce}",
                        extra={"prospect_id": prospect_id},
                    )

        # Convert Pydantic model to dict for state
        prospect_dict = prospect.model_dump()

        # Inject campaign service_area into prospect_data
        # The intent summarizer uses this as fallback when behavioral signals are weak
        if campaign_service_area:
            prospect_dict["campaign_service_area"] = campaign_service_area

        logger.info(
            "Fetched prospect from WordPress",
            extra={
                "prospect_id": prospect_id,
                "company": prospect.company_name,
                "room": prospect.current_room,
                "lead_score": prospect.lead_score,
                "campaign_service_area": campaign_service_area,
            },
        )

        return {
            "prospect_data": prospect_dict,
            "current_step": "fetch_prospect_data",
        }

    except Exception as e:
        logger.error(
            f"Failed to fetch prospect {prospect_id}: {e}",
            extra={"prospect_id": prospect_id},
        )
        return {
            "error": f"Failed to fetch prospect {prospect_id}: {e}",
            "current_step": "fetch_prospect_data",
        }


def _route_after_fetch(state: AgentState) -> Literal["analyze_intent", "handle_error"]:
    # Route after prospect data fetch
    # Errors if WordPress is unavailable or prospect not found

    if state.get("error"):
        return "handle_error"
    if state.get("prospect_data") is None:
        return "handle_error"
    return "analyze_intent"


def route_after_intent(state: AgentState) -> Literal["rank_assets", "handle_error"]:
    # Determine next step after intent analysis
    # Routes to error handling if analysis failed,
    # otherwise continues to asset ranking

    if state.get("error"):
        return "handle_error"
    if state.get("intent_profile") is None:
        return "handle_error"
    return "rank_assets"


def _route_after_rank(state: AgentState) -> Literal["compose_email", "handle_error"]:
    # Route after asset ranking
    # Errors from rank_assets (no content, exhausted, WP unavailable)
    # are caught by rank_assets_node and stored in state["error"]

    if state.get("error"):
        return "handle_error"
    if state.get("selected_content") is None:
        return "handle_error"
    return "compose_email"


async def rank_assets_node(state: AgentState) -> dict[str, Any]:
    # Wrapper around rank_assets that catches ValueError
    # and converts to state error (so the graph can route to handle_error)

    try:
        return await rank_assets(state)
    except ValueError as e:
        logger.error(
            f"Content selection failed: {e}",
            extra={"prospect_id": state.get("prospect_id", 0)},
        )
        return {
            "ranked_assets": [],
            "selected_content": None,
            "error": str(e),
        }


def _route_after_guardrails(
    state: AgentState,
) -> Literal["write_back_email", "interpret_revisions", "handle_error"]:
    # Route after guardrail inspection
    #
    # - Passed → write_back_email
    # - Failed + revision_count < MAX → interpret_revisions → compose_email loop
    # - Failed + revision_count >= MAX → handle_error (requires human approval)

    guardrail_result = state.get("guardrail_result")
    revision_count = state.get("revision_count", 0)

    if guardrail_result is None or guardrail_result.passed:
        return "write_back_email"

    if revision_count >= MAX_REVISION_ATTEMPTS:
        logger.warning(
            f"Max revision attempts ({MAX_REVISION_ATTEMPTS}) reached, "
            f"flagging for human review",
            extra={"prospect_id": state.get("prospect_id", 0)},
        )
        return "handle_error"

    return "interpret_revisions"


def handle_error(state: AgentState) -> dict:
    # Handle workflow errors gracefully
    # Logs the error and marks workflow as requiring review

    error = state.get("error", "Unknown error in workflow")
    logger.error(f"Workflow error: {error}")
    return {"requires_human_approval": True}


async def write_back_email(state: AgentState) -> dict[str, Any]:
    # Write the generated email back to WordPress via store-external endpoint
    #
    # Only writes back if:
    #   - No errors in pipeline
    #   - Email was generated
    #   - Guardrails passed
    #   - WordPress auth is configured
    #
    # email_number priority:
    #   1. state["email_number"] — set by WordPress before calling us (preferred)
    #   2. email_sequence_position + 1 — fallback derivation from prospect data
    #
    # Non-fatal: if write-back fails, logs warning but does not set error.
    # The email is still available in the pipeline response.

    prospect_id = state["prospect_id"]

    # Skip write-back if pipeline had errors
    if state.get("error"):
        logger.info(
            "Skipping write-back: pipeline has error",
            extra={"prospect_id": prospect_id},
        )
        return {"current_step": "write_back_email"}

    # Skip if no email was generated
    generated_email = state.get("generated_email")
    if not generated_email:
        logger.info(
            "Skipping write-back: no generated email",
            extra={"prospect_id": prospect_id},
        )
        return {"current_step": "write_back_email"}

    # Skip if guardrails failed
    guardrail = state.get("guardrail_result")
    if guardrail and not guardrail.passed:
        logger.info(
            "Skipping write-back: guardrail violations",
            extra={
                "prospect_id": prospect_id,
                "violations": guardrail.violation_count,
            },
        )
        return {"current_step": "write_back_email"}

    # Skip if WordPress not configured
    if not settings.has_wordpress_auth:
        logger.info(
            "Skipping write-back: no WordPress auth configured",
            extra={"prospect_id": prospect_id},
        )
        return {"current_step": "write_back_email"}

    # Extract needed data from state
    prospect_data = state.get("prospect_data", {})
    selected = state.get("selected_content")

    # Determine room_type from prospect data
    room_type = prospect_data.get("current_room", "problem")

    # email_number: use WP-reserved slot when available, otherwise derive
    email_number = state.get("email_number")
    if not email_number:
        email_sequence_position = prospect_data.get("email_sequence_position", 0)
        email_number = email_sequence_position + 1
        logger.debug(
            "email_number not in state, derived from sequence_position",
            extra={"prospect_id": prospect_id, "email_number": email_number},
        )

    # Build subject line
    intent = state.get("intent_profile")
    if selected and selected.title:
        subject = selected.title
    elif intent and intent.pain_points:
        subject = f"Thoughts on {intent.pain_points[0].lower()}"
    else:
        company = prospect_data.get("company_name", "your team")
        subject = f"A resource for {company}"

    # Get selected content URL
    url_included = selected.url if selected else None

    try:
        from services.wordpress_client import WordPressClient

        async with WordPressClient() as wp:
            result = await wp.store_generated_email(
                prospect_id=prospect_id,
                room_type=room_type,
                email_number=email_number,
                subject=subject,
                body_html=generated_email,
                body_text="",  # WordPress will strip_tags as fallback
                url_included=url_included,
            )

        logger.info(
            "Write-back to WordPress succeeded",
            extra={
                "prospect_id": prospect_id,
                "tracking_id": result.get("data", {}).get("email_tracking_id"),
                "room_type": room_type,
                "email_number": email_number,
            },
        )

        return {
            "writeback_result": result.get("data"),
            "current_step": "write_back_email",
        }

    except Exception as e:
        # Non-fatal — log warning but don't fail the pipeline
        logger.warning(
            f"Write-back to WordPress failed (non-fatal): {e}",
            extra={"prospect_id": prospect_id},
        )
        return {
            "writeback_result": {"error": str(e)},
            "current_step": "write_back_email",
        }


# =============================================================================
# Graph Construction
# =============================================================================

def create_email_generation_graph() -> StateGraph:
    # Build the email generation workflow graph
    #
    # Returns an uncompiled StateGraph that can be compiled with
    # optional checkpointing for human-in-the-loop workflows

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("fetch_prospect_data", fetch_prospect_data)
    workflow.add_node("analyze_intent", analyze_intent)
    workflow.add_node("rank_assets", rank_assets_node)
    workflow.add_node("compose_email", compose_email_v2)
    workflow.add_node("inspect_guardrails", inspect_guardrails)
    workflow.add_node("interpret_revisions", interpret_revisions)
    workflow.add_node("write_back_email", write_back_email)
    workflow.add_node("handle_error", handle_error)

    # Set entry point - fetch data first
    workflow.set_entry_point("fetch_prospect_data")

    # fetch_prospect_data -> route based on error or continue
    workflow.add_conditional_edges(
        "fetch_prospect_data",
        _route_after_fetch,
        {
            "analyze_intent": "analyze_intent",
            "handle_error": "handle_error",
        },
    )

    # Add conditional edge after intent analysis
    workflow.add_conditional_edges(
        "analyze_intent",
        route_after_intent,
        {
            "rank_assets": "rank_assets",
            "handle_error": "handle_error",
        },
    )

    # rank_assets -> route based on error or continue
    workflow.add_conditional_edges(
        "rank_assets",
        _route_after_rank,
        {
            "compose_email": "compose_email",
            "handle_error": "handle_error",
        },
    )
    workflow.add_edge("compose_email", "inspect_guardrails")

    # inspect_guardrails -> route: pass → write_back, fail → revision loop or error
    workflow.add_conditional_edges(
        "inspect_guardrails",
        _route_after_guardrails,
        {
            "write_back_email": "write_back_email",
            "interpret_revisions": "interpret_revisions",
            "handle_error": "handle_error",
        },
    )

    # Revision loop: interpret_revisions → compose_email (which re-runs guardrails)
    workflow.add_edge("interpret_revisions", "compose_email")

    workflow.add_edge("write_back_email", END)
    workflow.add_edge("handle_error", END)

    return workflow


# Create compiled graph for direct use
# Can be imported and invoked: email_generation_graph.invoke(state)
email_generation_graph = create_email_generation_graph().compile()


# =============================================================================
# Entry Point
# =============================================================================

async def run_email_generation(
    prospect_id: int,
    campaign_id: int,
    prospect_data: dict | None = None,
    email_number: int | None = None,
) -> AgentState:
    # Run the email generation workflow for a prospect
    #
    # Args:
    #     prospect_id: ID of the prospect in rtr_prospects table
    #     campaign_id: ID of the campaign in dr_campaign_settings table
    #     prospect_data: Optional pre-fetched prospect data dict.
    #     email_number: WP-reserved email slot (1-5). When set, write_back_email
    #                   uses this slot so the correct icon turns green in the UI.
    #
    # Returns:
    #     Final AgentState with ranked assets, generated email, and guardrail results

    from models.state import create_initial_state

    initial_state = create_initial_state(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
        prospect_data=prospect_data,
        email_number=email_number,
    )

    logger.info(
        "Starting email generation workflow",
        extra={
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "email_number": email_number,
            "has_prospect_data": prospect_data is not None,
        },
    )

    result = await email_generation_graph.ainvoke(initial_state)

    logger.info(
        "Email generation workflow complete",
        extra={
            "prospect_id": prospect_id,
            "has_recommendations": len(result.get("ranked_assets", [])) > 0,
            "has_email": result.get("generated_email") is not None,
            "error": result.get("error"),
        },
    )

    return result
