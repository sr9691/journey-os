# agents/email/compose_field_note.py
# New email generation node that replaces the old compose_email
# Chains: convert intent → extract insights → build template →
#         assemble context → Gemini JSON → parse → fallback
# Writes: generated_email, prompt_components, content_insights, generation_config

from __future__ import annotations

import json
import logging
from typing import Any

from config.settings import settings
from models.state import AgentState

logger = logging.getLogger(__name__)


# ============================================================================
# LangGraph Node Function
# ============================================================================

async def compose_email_v2(state: AgentState) -> dict[str, Any]:
    # New email generation node — uses the Field Note pipeline for Problem Room,
    # standard pipeline for Solution/Offer rooms.
    # Falls back to the old template composer if Gemini is unavailable.

    prospect_id = state.get("prospect_id", 0)
    prospect_data = state.get("prospect_data", {})
    old_intent = state.get("intent_profile")
    selected_content = state.get("selected_content")

    logger.info(
        "compose_email_v2: starting",
        extra={
            "prospect_id": prospect_id,
            "has_intent": old_intent is not None,
            "has_content": selected_content is not None,
        },
    )

    if not old_intent or not selected_content:
        logger.warning(
            "Missing intent_profile or selected_content, skipping email generation",
            extra={"prospect_id": prospect_id},
        )
        return {
            "generated_email": None,
            "current_step": "compose_email_v2",
        }

    # ------------------------------------------------------------------
    # 1. Convert old state.ProspectIntent → new models.prospect.ProspectIntent
    # ------------------------------------------------------------------
    from models.prospect import from_state_intent, ContentAsset, Room

    new_intent = from_state_intent(old_intent, prospect_data)

    # Convert RankedAsset to ContentAsset for the new pipeline
    content_asset = _ranked_asset_to_content_asset(selected_content)

    # Determine email format
    from agents.email.room_templates import EMAIL_FORMAT_FIELD_NOTE, EMAIL_FORMAT_STANDARD
    email_format = state.get("email_format")
    if not email_format:
        email_format = (
            EMAIL_FORMAT_FIELD_NOTE if new_intent.current_room == Room.PROBLEM
            else EMAIL_FORMAT_STANDARD
        )

    week_number = state.get("week_number")

    # ------------------------------------------------------------------
    # 2a. Fetch full article content from URL (best-effort)
    # ------------------------------------------------------------------
    if content_asset.url and not content_asset.article_body:
        article_text = await _fetch_article_body(content_asset.url)
        if article_text:
            content_asset.article_body = article_text

    # ------------------------------------------------------------------
    # 2b. Extract insights (uses article_body when available)
    # ------------------------------------------------------------------
    content_insights = state.get("content_insights")
    if content_insights is None:
        content_insights = _try_extract_insights(
            selected_content, new_intent, prospect_data,
        )

    # ------------------------------------------------------------------
    # 3. Build prompt template (7 components)
    # ------------------------------------------------------------------
    from agents.email.prompt_template_builder import build_prompt_template

    prompt_components = build_prompt_template(
        intent_profile=new_intent,
        selected_content=content_asset,
        prospect_data=prospect_data,
        email_format=email_format,
        content_insights=content_insights,
        week_number=week_number,
    )

    # ------------------------------------------------------------------
    # 4. Assemble full Gemini payload
    # ------------------------------------------------------------------
    from agents.email.context_assembler import assemble_email_context

    gen_context = assemble_email_context(
        intent_profile=new_intent,
        prompt_components=prompt_components,
        selected_content=content_asset,
        prospect_data=prospect_data,
        content_insights=content_insights,
        email_format=email_format,
    )

    # ------------------------------------------------------------------
    # 4b. Append revision instructions if in revision loop
    # ------------------------------------------------------------------
    revision_instructions = state.get("revision_instructions")
    if revision_instructions:
        gen_context["prompt"] = (
            gen_context["prompt"] + "\n\n" + revision_instructions
        )
        logger.info(
            "Revision instructions appended to prompt",
            extra={
                "prospect_id": prospect_id,
                "revision_count": state.get("revision_count", 0),
            },
        )

    # ------------------------------------------------------------------
    # 5. Call Gemini for email generation (or fall back)
    # ------------------------------------------------------------------
    email_text = None
    gen_source = "template"

    if settings.has_gemini_key:
        email_text = await _generate_with_gemini(gen_context)
        if email_text:
            gen_source = "gemini"

    if email_text is None:
        # Fall back to old template-based generation
        email_text = _fallback_template(prospect_data, new_intent, content_asset)
        gen_source = "template"

    logger.info(
        "compose_email_v2: complete",
        extra={
            "prospect_id": prospect_id,
            "room": new_intent.current_room.value,
            "format": email_format,
            "source": gen_source,
            "length": len(email_text) if email_text else 0,
        },
    )

    return {
        "generated_email": email_text,
        "prompt_components": prompt_components,
        "content_insights": content_insights,
        "generation_config": gen_context,
        "current_step": "compose_email_v2",
    }


# ============================================================================
# Gemini Generation
# ============================================================================

async def _generate_with_gemini(gen_context: dict[str, Any]) -> str | None:
    # Call Gemini with the assembled context, parse JSON response
    # Returns the full email text (subject + body) or None on failure

    try:
        from services.llm_client import GeminiClient, LLMClientError

        prompt = gen_context.get("prompt", "")
        system = gen_context.get("system_instruction", "")
        config = gen_context.get("generation_config", {})
        temperature = config.get("temperature", 0.7)

        async with GeminiClient() as gemini:
            result = await gemini.complete_json(
                system=system,
                user_message=prompt,
                temperature=temperature,
            )

        # Result should be {"subject": "...", "body": "..."}
        subject = result.get("subject", "")
        body = result.get("body", "")

        if not body:
            logger.warning("Gemini returned empty body")
            return None

        # Combine subject + body into full email text
        # The guardrail inspector and write-back node will use this
        email_text = f"Subject: {subject}\n\n{body}" if subject else body

        logger.info("Gemini Field Note generation succeeded")
        return email_text

    except Exception as e:
        logger.warning(f"Gemini generation failed, falling back to template: {e}")
        return None


# ============================================================================
# Fallback Template Generation
# ============================================================================

def _fallback_template(
    prospect_data: dict[str, Any],
    intent: Any,
    content_asset: Any,
) -> str:
    # Use the old email_composer template logic as fallback

    from agents.generation.email_composer import _compose_with_template, _build_email_context
    from models.state import RankedAsset

    # Build a RankedAsset-compatible object for the old code
    ranked = RankedAsset(
        asset_id=content_asset.asset_id if hasattr(content_asset, "asset_id") else 0,
        url=content_asset.url if hasattr(content_asset, "url") else "",
        title=content_asset.title if hasattr(content_asset, "title") else "Resource",
        room=content_asset.room if hasattr(content_asset, "room") else "problem",
        score=content_asset.score if hasattr(content_asset, "score") else 0.0,
    )

    # Build the old-style ProspectIntent for _build_email_context
    from models.state import ProspectIntent as OldIntent
    old_intent = OldIntent(
        prospect_id=intent.prospect_id,
        service_area=intent.service_area,
        pain_points=[
            p if isinstance(p, str) else str(p) for p in intent.pain_points
        ],
        confidence=intent.confidence,
        urgency_level=intent.urgency_level,
        decision_stage=intent.decision_stage,
        key_questions=intent.key_questions,
        analysis_source=intent.analysis_source,
    )

    room = intent.current_room.value
    email_context = _build_email_context(prospect_data, old_intent, ranked, room)
    return _compose_with_template(email_context, room)


# ============================================================================
# Insight Extraction (best-effort, sync wrapper)
# ============================================================================

def _try_extract_insights(
    selected_content: Any,
    intent: Any,
    prospect_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    # Try to extract insights using the insight_extractor module
    # Returns None if extraction isn't possible (no LLM key, etc.)

    try:
        from agents.email.insight_extractor import _fallback_extract_insights
        return _fallback_extract_insights(selected_content, intent)
    except Exception as e:
        logger.debug(f"Insight extraction skipped: {e}")
        return None


# ============================================================================
# Helpers
# ============================================================================

def _ranked_asset_to_content_asset(ranked: Any) -> Any:
    # Convert a RankedAsset (from state) to ContentAsset (for new pipeline)

    from models.prospect import ContentAsset

    if hasattr(ranked, "model_dump"):
        data = ranked.model_dump()
    elif isinstance(ranked, dict):
        data = ranked
    else:
        data = {}

    return ContentAsset(
        asset_id=data.get("asset_id", 0),
        url=data.get("url", ""),
        title=data.get("title", "Resource"),
        room=data.get("room", "problem"),
        content_type=data.get("content_type", "article"),
        summary=data.get("summary"),
        article_body=data.get("article_body"),
        score=data.get("score", 0.0),
        match_reasons=data.get("match_reasons", []),
    )


async def _fetch_article_body(url: str) -> str | None:
    # Fetch full article text from URL for content grounding
    # Returns None if fetch fails or URL is a placeholder

    try:
        from services.article_fetcher import fetch_article_text
        return await fetch_article_text(url)
    except Exception as e:
        logger.debug(f"Article fetch skipped: {e}")
        return None


# ============================================================================
# Business-Impact Fallback Content
# ============================================================================

# Industry-specific business impact themes for when no content is available
_INDUSTRY_IMPACT_THEMES: dict[str, dict[str, str]] = {
    "healthcare": {
        "title": "The Hidden Operational Costs Most Healthcare Organizations Miss",
        "summary": (
            "Healthcare organizations often absorb operational inefficiencies "
            "as normal — manual handoffs, duplicated data entry, compliance "
            "workarounds — without measuring the cumulative cost. These small "
            "frictions compound into margin pressure that shows up as 'just how "
            "things work' instead of a solvable problem."
        ),
    },
    "financial services": {
        "title": "Where Financial Services Firms Lose Time Without Realizing It",
        "summary": (
            "Financial services firms face a unique combination of regulatory "
            "pressure and operational complexity. The cost often hides in "
            "compliance workarounds, manual reconciliation, and reporting "
            "processes that haven't been re-examined in years."
        ),
    },
    "manufacturing": {
        "title": "The Operational Drag Most Manufacturers Accept as Normal",
        "summary": (
            "Manufacturing operations accumulate process debt over time — "
            "manual scheduling, disconnected systems, reactive maintenance. "
            "Each workaround seems small, but together they create drag that "
            "shows up as missed deadlines, margin pressure, and scaling friction."
        ),
    },
    "technology": {
        "title": "Why Growing Tech Companies Hit Invisible Operational Ceilings",
        "summary": (
            "Tech companies often scale faster than their internal processes. "
            "What worked at 50 people breaks at 200. The symptoms — longer "
            "delivery cycles, more meetings, harder hiring — get blamed on "
            "growth when the real cause is process debt."
        ),
    },
    "retail": {
        "title": "The Cost of Operational Complexity in Retail",
        "summary": (
            "Retail operations juggle inventory, fulfillment, and customer "
            "experience across channels. The hidden cost is in the manual "
            "coordination — the spreadsheets, the workarounds, the tribal "
            "knowledge that holds everything together."
        ),
    },
}

_DEFAULT_IMPACT_THEME: dict[str, str] = {
    "title": "The Business Cost of Operational Friction You've Stopped Noticing",
    "summary": (
        "Most organizations absorb small operational inefficiencies as "
        "normal — manual workarounds, disconnected systems, tribal knowledge. "
        "Each one seems minor. Together, they create compounding drag on "
        "margins, speed, and team capacity. The problem isn't that these "
        "issues are hard to fix. It's that they've become invisible."
    ),
}


def _build_impact_fallback_content(
    prospect_data: dict[str, Any] | None,
    intent_profile: Any,
) -> Any:
    # Build a business-impact content asset when no ranked content is available
    # Uses industry context to create a relevant problem-awareness piece

    from models.state import RankedAsset

    industry = ""
    if prospect_data:
        industry = (prospect_data.get("industry") or "").lower()

    # Find best matching industry theme
    theme = _DEFAULT_IMPACT_THEME
    for industry_key, industry_theme in _INDUSTRY_IMPACT_THEMES.items():
        if industry_key in industry or industry in industry_key:
            theme = industry_theme
            break

    service_area = ""
    if hasattr(intent_profile, "service_area") and intent_profile.service_area:
        service_area = intent_profile.service_area

    return RankedAsset(
        asset_id=0,
        url="",
        title=theme["title"],
        room="problem",
        score=0.0,
        match_reasons=["business_impact_fallback"],
        content_type="insight",
        summary=theme["summary"],
    )
