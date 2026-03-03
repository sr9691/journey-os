# models/prospect.py
# Prospect and content models for the new email pipeline
# Room enum, ProspectIntent with room-aware fields, ContentAsset, determine_room
# Used by: agents/email/prompt_template_builder.py,
#          agents/email/context_assembler.py,
#          agents/email/insight_extractor.py

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Room Enum
# ============================================================================

class Room(str, Enum):
    # RTR methodology rooms based on lead score thresholds
    PROBLEM = "problem"
    SOLUTION = "solution"
    OFFER = "offer"


# ============================================================================
# Room Determination
# ============================================================================

# Thresholds from config/guardrails.py
ROOM_THRESHOLDS = {
    "problem_max": 40,
    "solution_max": 60,
    "offer_min": 61,
}


def determine_room(lead_score: int) -> Room:
    # Determine which RTR room a prospect belongs to based on lead score
    if lead_score <= ROOM_THRESHOLDS["problem_max"]:
        return Room.PROBLEM
    elif lead_score <= ROOM_THRESHOLDS["solution_max"]:
        return Room.SOLUTION
    else:
        return Room.OFFER


# ============================================================================
# ProspectIntent — extended model for the new email pipeline
# ============================================================================
# This model extends the original state.ProspectIntent with room-aware fields
# needed by prompt_template_builder and context_assembler.

class ProspectIntent(BaseModel):
    # Intent profile with room awareness for email generation

    prospect_id: int = Field(default=0, description="ID from rtr_prospects table")
    current_room: Room = Field(default=Room.PROBLEM, description="RTR room placement")
    lead_score: int = Field(default=0, description="Prospect lead score")

    service_area: str | None = Field(
        default=None,
        description="Primary service area interest (e.g. cloud-migration)",
    )
    related_areas: list[str] = Field(
        default_factory=list,
        description="Secondary service area interests",
    )
    pain_points: list[Any] = Field(
        default_factory=list,
        description="Identified pain points — strings or PainPoint objects",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Analysis confidence score",
    )

    # Urgency and decision signals
    urgency_level: str | None = Field(default=None, description="low, medium, high")
    urgency_signals: list[str] = Field(
        default_factory=list,
        description="Signals indicating urgency",
    )
    decision_stage: str | None = Field(
        default=None,
        description="awareness, consideration, decision",
    )
    key_questions: list[str] = Field(
        default_factory=list,
        description="Questions the prospect likely has",
    )
    analysis_source: str = Field(
        default="rules",
        description="How intent was derived: 'claude' or 'rules'",
    )


# ============================================================================
# ContentAsset — content link metadata for email integration
# ============================================================================

class ContentAsset(BaseModel):
    # A content asset to be referenced in an email

    asset_id: int = Field(default=0, description="ID from rtr_room_content_links")
    url: str = Field(default="", description="Content link URL")
    title: str = Field(default="Resource", description="Content title")
    room: str = Field(default="problem", description="Room: problem, solution, offer")
    content_type: str = Field(default="article", description="article, case_study, guide, etc.")
    summary: str | None = Field(default=None, description="Brief content summary")
    article_body: str | None = Field(default=None, description="Full article text fetched from URL")
    score: float = Field(default=0.0, description="Relevance score from asset ranker")
    match_reasons: list[str] = Field(
        default_factory=list,
        description="Why this asset was selected",
    )


# ============================================================================
# Conversion helper — bridge old state.ProspectIntent to new ProspectIntent
# ============================================================================

def from_state_intent(
    state_intent: Any,
    prospect_data: dict[str, Any] | None = None,
) -> ProspectIntent:
    # Convert the existing state.ProspectIntent (or dict) to the new
    # room-aware ProspectIntent used by the email pipeline

    if isinstance(state_intent, dict):
        lead_score = state_intent.get("lead_score", 0)
        if not lead_score and prospect_data:
            lead_score = prospect_data.get("lead_score", 0)

        return ProspectIntent(
            prospect_id=state_intent.get("prospect_id", 0),
            current_room=determine_room(lead_score),
            lead_score=lead_score,
            service_area=state_intent.get("service_area"),
            related_areas=state_intent.get("related_areas", []),
            pain_points=state_intent.get("pain_points", []),
            confidence=state_intent.get("confidence", 0.5),
            urgency_level=state_intent.get("urgency_level"),
            urgency_signals=state_intent.get("urgency_signals", []),
            decision_stage=state_intent.get("decision_stage"),
            key_questions=state_intent.get("key_questions", []),
            analysis_source=state_intent.get("analysis_source", "rules"),
        )

    # If it's a Pydantic model (old state.ProspectIntent), extract fields
    if hasattr(state_intent, "model_dump"):
        data = state_intent.model_dump()
    elif hasattr(state_intent, "__dict__"):
        data = vars(state_intent)
    else:
        data = {}

    lead_score = data.get("lead_score", 0)
    if not lead_score and prospect_data:
        lead_score = prospect_data.get("lead_score", 0)

    return ProspectIntent(
        prospect_id=data.get("prospect_id", 0),
        current_room=determine_room(lead_score),
        lead_score=lead_score,
        service_area=data.get("service_area"),
        related_areas=data.get("related_areas", []),
        pain_points=data.get("pain_points", []),
        confidence=data.get("confidence", 0.5),
        urgency_level=data.get("urgency_level"),
        urgency_signals=data.get("urgency_signals", []),
        decision_stage=data.get("decision_stage"),
        key_questions=data.get("key_questions", []),
        analysis_source=data.get("analysis_source", "rules"),
    )
