# =============================================================================
# Email Generation Workflow Graph
# =============================================================================
#
# A LangGraph workflow that orchestrates the content recommendation
# and email generation process for DirectReach prospects.
#
# Flow:
# 1. analyze_intent - Extract intent signals from prospect data
# 2. rank_assets - Score and rank content for the prospect
# 3. (Future: guardrail_inspect - Check room compliance)
# 4. (Future: generate_email - Create personalized email with Gemini)
#
# MVP version: 2 nodes to prove graph execution works.
# =============================================================================

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from models.state import AgentState
from agents.matching.intent_summarizer import analyze_intent
from agents.matching.asset_ranker import rank_assets

logger = logging.getLogger(__name__)


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


def create_email_generation_graph() -> StateGraph:
    # Build the email generation workflow graph
    #
    # Returns an uncompiled StateGraph that can be compiled with
    # optional checkpointing for human-in-the-loop workflows

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("analyze_intent", analyze_intent)
    workflow.add_node("rank_assets", rank_assets)
    workflow.add_node("handle_error", handle_error)

    # Set entry point
    workflow.set_entry_point("analyze_intent")

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


# Async entry point for production use
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
    #     prospect_data: Optional pre-fetched prospect data dict
    #
    # Returns:
    #     Final AgentState with ranked assets and recommendations

    from models.state import create_initial_state

    initial_state = create_initial_state(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
        prospect_data=prospect_data,
    )

    # If no prospect data provided, use mock data for MVP
    # Production: fetch from WordPress via WordPressClient
    if initial_state["prospect_data"] is None:
        initial_state["prospect_data"] = {
            "id": prospect_id,
            "campaign_id": campaign_id,
            "current_room": "problem",
            "lead_score": 35,
            "company_name": "Acme Health Systems",
            "contact_name": "Sarah Johnson",
            "job_title": "VP of Operations",
            "industry": "Healthcare",
            "employee_count": "1001-5000",
        }

    logger.info(
        "Starting email generation workflow",
        extra={"prospect_id": prospect_id, "campaign_id": campaign_id},
    )

    # Run the graph
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