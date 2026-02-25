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
# 4. (Future: guardrail_inspect - Check room compliance)
# 5. (Future: generate_email - Create personalized email with Gemini)
#
# Phase 1: Added real WordPress data fetching with fallback to mock.
# =============================================================================

import logging
from typing import Any, Literal

from langgraph.graph import StateGraph, END

from config.settings import settings
from models.state import AgentState
from agents.matching.intent_summarizer import analyze_intent
from agents.matching.asset_ranker import rank_assets

logger = logging.getLogger(__name__)


# =============================================================================
# Mock Data (fallback when WordPress is unreachable)
# =============================================================================

MOCK_PROSPECT_DATA: dict[str, Any] = {
    "id": 0,  # Will be overwritten with actual prospect_id
    "campaign_id": 0,  # Will be overwritten with actual campaign_id
    "current_room": "problem",
    "lead_score": 35,
    "company_name": "Acme Health Systems",
    "contact_name": "Sarah Johnson",
    "job_title": "VP of Operations",
    "industry": "Healthcare",
    "employee_count": "1001-5000",
}


# =============================================================================
# Graph Nodes
# =============================================================================

async def fetch_prospect_data(state: AgentState) -> dict[str, Any]:
    # Fetch prospect data from WordPress REST API
    # Falls back to mock data if WordPress is unreachable or unconfigured
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

    # Attempt to fetch from WordPress
    if settings.has_wordpress_auth:
        try:
            from services.wordpress_client import WordPressClient

            async with WordPressClient() as wp:
                prospect = await wp.get_prospect(prospect_id)

            # Convert Pydantic model to dict for state
            prospect_dict = prospect.model_dump()

            logger.info(
                "Fetched prospect from WordPress",
                extra={
                    "prospect_id": prospect_id,
                    "company": prospect.company_name,
                    "room": prospect.current_room,
                    "lead_score": prospect.lead_score,
                },
            )

            return {
                "prospect_data": prospect_dict,
                "current_step": "fetch_prospect_data",
            }

        except Exception as e:
            logger.warning(
                f"WordPress fetch failed, falling back to mock data: {e}",
                extra={"prospect_id": prospect_id},
            )
    else:
        logger.info(
            "No WordPress auth configured, using mock data",
            extra={"prospect_id": prospect_id},
        )

    # Fallback to mock data
    mock = MOCK_PROSPECT_DATA.copy()
    mock["id"] = prospect_id
    mock["campaign_id"] = campaign_id

    return {
        "prospect_data": mock,
        "current_step": "fetch_prospect_data",
    }


def route_after_intent(state: AgentState) -> Literal["rank_assets", "handle_error"]:
    # Determine next step after intent analysis
    # Routes to error handling if analysis failed,
    # otherwise continues to asset ranking

    if state.get("error"):
        return "handle_error"
    if state.get("intent_profile") is None:
        return "handle_error"
    return "rank_assets"


def handle_error(state: AgentState) -> dict:
    # Handle workflow errors gracefully
    # Logs the error and marks workflow as requiring review

    error = state.get("error", "Unknown error in workflow")
    logger.error(f"Workflow error: {error}")
    return {"requires_human_approval": True}


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
    workflow.add_node("rank_assets", rank_assets)
    workflow.add_node("handle_error", handle_error)

    # Set entry point - fetch data first
    workflow.set_entry_point("fetch_prospect_data")

    # fetch_prospect_data always proceeds to analyze_intent
    workflow.add_edge("fetch_prospect_data", "analyze_intent")

    # Add conditional edge after intent analysis
    workflow.add_conditional_edges(
        "analyze_intent",
        route_after_intent,
        {
            "rank_assets": "rank_assets",
            "handle_error": "handle_error",
        },
    )

    # Terminal edges
    workflow.add_edge("rank_assets", END)
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
) -> AgentState:
    # Run the email generation workflow for a prospect
    #
    # This is the main entry point for triggering email generation
    # from WordPress webhooks or other external systems.
    #
    # Args:
    #     prospect_id: ID of the prospect in rtr_prospects table
    #     campaign_id: ID of the campaign in dr_campaign_settings table
    #     prospect_data: Optional pre-fetched prospect data dict.
    #                    If None, fetch_prospect_data node will attempt
    #                    to fetch from WordPress (or fall back to mock).
    #
    # Returns:
    #     Final AgentState with ranked assets and recommendations

    from models.state import create_initial_state

    initial_state = create_initial_state(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
        prospect_data=prospect_data,
    )

    logger.info(
        "Starting email generation workflow",
        extra={
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "has_prospect_data": prospect_data is not None,
        },
    )

    # Run the graph — fetch_prospect_data will handle data retrieval
    result = await email_generation_graph.ainvoke(initial_state)

    logger.info(
        "Email generation workflow complete",
        extra={
            "prospect_id": prospect_id,
            "has_recommendations": len(result.get("ranked_assets", [])) > 0,
            "error": result.get("error"),
        },
    )

    return result
