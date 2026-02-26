# =============================================================================
# LangGraph State Definitions
# =============================================================================
#
# AgentState TypedDict is the single source of truth passed between all nodes.
# Each agent reads what it needs and returns only the keys it updates.
#
# Data models use Pydantic BaseModel for validation.
# AgentState uses TypedDict (required by LangGraph for state management).
# =============================================================================

from typing import TypedDict, Any

from pydantic import BaseModel, Field


# =============================================================================
# Pydantic Models (validated data structures)
# =============================================================================

class ProspectIntent(BaseModel):
    # Intent profile extracted from prospect data
    # Populated by the intent_summarizer agent
    #
    # Phase 3: Expanded with urgency_level, decision_stage, key_questions,
    # and analysis_source to track whether Claude or rules produced the intent.

    prospect_id: int = Field(..., description="ID from rtr_prospects table")
    service_area: str | None = Field(
        default=None,
        description="Primary service area interest (e.g. cloud-migration, ai-development)",
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="Identified pain points from engagement signals",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Analysis confidence score",
    )
    # Phase 3 additions — populated by Claude API when available
    urgency_level: str | None = Field(
        default=None,
        description="Prospect urgency: low, medium, high",
    )
    decision_stage: str | None = Field(
        default=None,
        description="Buying stage: awareness, consideration, decision",
    )
    key_questions: list[str] = Field(
        default_factory=list,
        description="Questions the prospect likely has based on their signals",
    )
    analysis_source: str = Field(
        default="rules",
        description="How intent was derived: 'claude' or 'rules'",
    )


class GuardrailViolation(BaseModel):
    # A single guardrail violation found in content
    # Phase 4: Used by the Guardrail Inspector node

    violation_type: str = Field(..., description="ViolationType enum value")
    matched_text: str = Field(..., description="The text that triggered the violation")
    context: str = Field(default="", description="Surrounding text for context")
    severity: str = Field(
        default="warning",
        description="Severity: 'warning' or 'block'",
    )


class GuardrailResult(BaseModel):
    # Result of guardrail inspection on content
    # Phase 4: Populated by the guardrail_inspector agent

    passed: bool = Field(default=True, description="Whether content passed all guardrails")
    room: str = Field(..., description="Room the content was checked against")
    violations: list[GuardrailViolation] = Field(
        default_factory=list,
        description="List of violations found",
    )
    violation_count: int = Field(default=0, description="Total number of violations")
    checked_text: str = Field(default="", description="The text that was inspected")
    suggestion: str = Field(
        default="",
        description="Human-readable summary of what needs fixing",
    )


class RankedAsset(BaseModel):
    # Content asset with relevance score
    # Populated by the asset_ranker agent

    asset_id: int = Field(..., description="ID from rtr_room_content_links table")
    url: str = Field(..., description="Content link URL")
    title: str = Field(..., description="Content link title")
    room: str = Field(..., description="Room type: problem, solution, or offer")
    score: float = Field(default=0.0, description="Weighted relevance score")
    match_reasons: list[str] = Field(
        default_factory=list,
        description="Scoring criteria that contributed to the score",
    )


# =============================================================================
# LangGraph State (TypedDict for graph compatibility)
# =============================================================================

class AgentState(TypedDict, total=False):
    # Shared state for email generation workflow
    # total=False allows agents to return partial updates
    # Each agent reads what it needs and returns only modified keys

    # Input - set by workflow trigger
    prospect_id: int
    campaign_id: int

    # Prospect data - populated by data fetch from WordPress
    prospect_data: dict[str, Any] | None

    # Intent analysis - populated by intent_summarizer
    intent_profile: ProspectIntent | None

    # Content matching - populated by asset_ranker
    ranked_assets: list[RankedAsset]
    selected_content: RankedAsset | None

    # Email generation - populated by email assembler (future)
    email_context: dict[str, Any] | None
    generated_email: str | None

    # Quality control - populated by guardrail_inspector (Phase 4)
    guardrail_result: GuardrailResult | None
    revision_count: int

    # Control flow
    current_step: str
    error: str | None
    requires_human_approval: bool


# =============================================================================
# State Factory
# =============================================================================

def create_initial_state(
    prospect_id: int,
    campaign_id: int,
    prospect_data: dict[str, Any] | None = None,
) -> AgentState:
    # Factory for properly initialized state
    return AgentState(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
        prospect_data=prospect_data,
        intent_profile=None,
        ranked_assets=[],
        selected_content=None,
        email_context=None,
        generated_email=None,
        guardrail_result=None,
        revision_count=0,
        current_step="init",
        error=None,
        requires_human_approval=False,
    )
