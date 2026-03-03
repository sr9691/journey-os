# agents/email/insight_extractor.py
# Insight Extractor Agent
# Pre-generation node that extracts 8-12 grounded insights from content
# These feed into email generation for specificity (quick tests, small moves)

from __future__ import annotations

import json
import logging
from typing import Any

from models.state import AgentState
from models.prospect import ContentAsset
from models.prospect import ProspectIntent, Room

logger = logging.getLogger(__name__)


# ============================================================================
# Extraction Prompt
# ============================================================================

INSIGHT_EXTRACTION_SYSTEM = """You are an expert at extracting actionable, grounded insights from articles.

Your job is to read the provided content and extract 8-12 specific, practical insights.

Each insight must be:
- Grounded in the article (not invented)
- Specific enough to build a "quick test" or "small move" around
- Operational / process-oriented (not abstract strategy)

Output ONLY valid JSON. No markdown, no backticks, no preamble.

JSON format:
{
    "insights": [
        {
            "insight": "Brief description of the insight",
            "type": "quick_test | small_move | reframe | metric | anti_pattern",
            "specificity": "high | medium",
            "applicable_roles": ["VP Ops", "CFO", "CTO"]
        }
    ],
    "core_reframe": "The main 'looks like X but actually Y' from this content",
    "problem_theme": "One-sentence summary of the core problem"
}"""

INSIGHT_EXTRACTION_PROMPT = """Extract 8-12 grounded insights from the following content.

Focus on insights that would be useful for a {role} at a {industry} company.

## Content Title: {title}

## Content Summary:
{summary}

{article_body_section}

## Content URL: {url}

## Prospect Context:
- Industry: {industry}
- Role: {role}
- Pain points: {pain_points}
- Service area interest: {service_area}

Extract insights now. Every insight MUST be grounded in the article content above. Output ONLY JSON."""


# ============================================================================
# Fallback Extraction (rule-based, no LLM)
# ============================================================================

def _fallback_extract_insights(
    content: ContentAsset | dict[str, Any] | None,
    intent_profile: ProspectIntent | None,
) -> dict[str, Any]:
    # Rule-based fallback when Claude/Gemini unavailable
    # Returns a minimal insight set based on available metadata

    insights = []
    core_reframe = "This looks like a people problem but it's actually a process problem."
    problem_theme = "Operational friction that compounds over time."

    if content:
        content_dict = content if isinstance(content, dict) else {}
        if hasattr(content, "model_dump"):
            content_dict = content.model_dump()

        title = content_dict.get("title", "")
        summary = content_dict.get("summary", "")
        content_type = content_dict.get("content_type", "article")

        # Generate generic insights from metadata
        if title:
            insights.append({
                "insight": f"Key concept from: {title}",
                "type": "reframe",
                "specificity": "medium",
                "applicable_roles": [],
            })

        if summary:
            # Split summary into sentences and treat each as a potential insight
            sentences = [s.strip() for s in summary.split(".") if len(s.strip()) > 20]
            for sentence in sentences[:6]:
                insights.append({
                    "insight": sentence,
                    "type": "small_move",
                    "specificity": "medium",
                    "applicable_roles": [],
                })

    # Pad with generic insights if we have fewer than 8
    generic_insights = [
        {
            "insight": "Track rework frequency as a leading indicator",
            "type": "metric",
            "specificity": "medium",
            "applicable_roles": ["VP Ops", "Director"],
        },
        {
            "insight": "Pilot one workflow change before scaling",
            "type": "small_move",
            "specificity": "medium",
            "applicable_roles": ["VP Ops", "Manager"],
        },
        {
            "insight": "Classify issues by root cause, not symptom",
            "type": "quick_test",
            "specificity": "medium",
            "applicable_roles": ["VP Ops", "Director"],
        },
    ]

    while len(insights) < 8 and generic_insights:
        insights.append(generic_insights.pop(0))

    return {
        "insights": insights,
        "core_reframe": core_reframe,
        "problem_theme": problem_theme,
        "extraction_method": "fallback",
    }


# ============================================================================
# LLM-based Extraction
# ============================================================================

def _build_article_body_section(content_dict: dict[str, Any]) -> str:
    # Build the article body section for the extraction prompt
    # Returns full article text block or empty string if unavailable

    article_body = content_dict.get("article_body")
    if not article_body:
        return ""

    return (
        "## Full Article Content:\n"
        f"{article_body}\n"
    )


def _extract_insights_with_llm(
    content: ContentAsset | dict[str, Any],
    intent_profile: ProspectIntent,
    prospect_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Extract insights using Claude API
    # Falls back to rule-based if unavailable

    try:
        from services.llm_client import get_claude_client
        client = get_claude_client()
    except (ImportError, ValueError) as e:
        logger.warning(f"Claude unavailable for insight extraction: {e}")
        return _fallback_extract_insights(content, intent_profile)

    content_dict = content if isinstance(content, dict) else {}
    if hasattr(content, "model_dump"):
        content_dict = content.model_dump()

    # Build the extraction prompt
    pain_points_str = ", ".join(
        [p.description if hasattr(p, "description") else str(p)
         for p in (intent_profile.pain_points or [])]
    ) or "general operational friction"

    role = ""
    industry = ""
    if prospect_data:
        role = prospect_data.get("job_title", "Operations Leader")
        industry = prospect_data.get("industry", "B2B Services")

    prompt = INSIGHT_EXTRACTION_PROMPT.format(
        title=content_dict.get("title", "Unknown"),
        summary=content_dict.get("summary", "No summary available"),
        article_body_section=_build_article_body_section(content_dict),
        url=content_dict.get("url", ""),
        industry=industry or "B2B Services",
        role=role or "Operations Leader",
        pain_points=pain_points_str,
        service_area=intent_profile.service_area or "general",
    )

    try:
        result = client.complete_json(
            prompt=prompt,
            system=INSIGHT_EXTRACTION_SYSTEM,
        )
        result["extraction_method"] = "claude"

        # Validate structure
        if "insights" not in result or len(result["insights"]) < 4:
            logger.warning("Claude returned fewer than 4 insights, supplementing with fallback")
            fallback = _fallback_extract_insights(content, intent_profile)
            result["insights"] = result.get("insights", []) + fallback["insights"]
            result["insights"] = result["insights"][:12]

        return result

    except Exception as e:
        logger.warning(f"Claude insight extraction failed: {e}, using fallback")
        return _fallback_extract_insights(content, intent_profile)


# ============================================================================
# LangGraph Node Function
# ============================================================================

def extract_insights(state: AgentState) -> dict[str, Any]:
    # LangGraph node: extract grounded insights from selected content
    # Runs BEFORE email generation to improve specificity
    # Returns dict with 'content_insights' key

    intent_profile = state.get("intent_profile")
    selected_content = state.get("selected_content")
    prospect_data = state.get("prospect_data")

    if not intent_profile:
        logger.error("No intent_profile in state for insight extraction")
        return {
            "content_insights": None,
            "error": "Missing intent_profile for insight extraction",
        }

    # Convert dict to ProspectIntent if needed
    if isinstance(intent_profile, dict):
        from models.prospect import ProspectIntent, determine_room
        intent_profile = ProspectIntent(
            prospect_id=intent_profile.get("prospect_id", 0),
            current_room=determine_room(intent_profile.get("lead_score", 0)),
            lead_score=intent_profile.get("lead_score", 0),
            service_area=intent_profile.get("service_area"),
            related_areas=intent_profile.get("related_areas", []),
            confidence=intent_profile.get("confidence", 0.5),
        )

    # Convert prospect_data dict if needed
    if prospect_data and hasattr(prospect_data, "model_dump"):
        prospect_data = prospect_data.model_dump()

    if selected_content:
        insights = _extract_insights_with_llm(
            content=selected_content,
            intent_profile=intent_profile,
            prospect_data=prospect_data,
        )
    else:
        logger.info("No selected_content, using fallback insight extraction")
        insights = _fallback_extract_insights(None, intent_profile)

    logger.info(
        "Insight extraction complete",
        extra={
            "prospect_id": intent_profile.prospect_id,
            "insight_count": len(insights.get("insights", [])),
            "method": insights.get("extraction_method", "unknown"),
        }
    )

    return {
        "content_insights": insights,
        "current_step": "insights_extracted",
    }
