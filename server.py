# =============================================================================
# FastAPI Webhook Server
# =============================================================================
#
# Provides HTTP endpoints for WordPress to trigger email generation
# and receive results. This is the CIS entry point for production use.
#
# Endpoints:
#   POST /process-prospect        - Trigger email generation (client_id + prospect_id)
#   POST /webhook/generate-email  - Trigger email generation for a prospect
#   POST /webhook/batch-generate  - Trigger batch email generation
#   GET  /health                  - Health check
#   GET  /health/ready            - Readiness check (validates API keys)
#
# WordPress Integration:
#   The WordPress plugin sends a POST to /webhook/generate-email when a
#   prospect enters a new room or needs a fresh email. The CIS runs the
#   full LangGraph pipeline and POSTs the result back to WordPress via
#   the callback_url provided in the request.
#
# Phase 6: End-to-End Testing & WordPress Webhook
# =============================================================================

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field

from config.settings import settings
from graphs.email_generation import run_email_generation

logger = logging.getLogger(__name__)

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Content Intelligence System",
    description="AI agent orchestration for B2B email generation",
    version="0.6.0",
)


# =============================================================================
# Request / Response Models
# =============================================================================

class GenerateEmailRequest(BaseModel):
    # Request body for email generation webhook.

    prospect_id: int = Field(..., description="ID from rtr_prospects table")
    campaign_id: int = Field(..., description="ID from dr_campaign_settings table")
    # email_number is the WP-reserved slot (1-5).
    # WordPress calculates this before calling us and sets the slot to 'generating'.
    # We use it in write_back_email so store-external writes to the correct slot.
    # If absent, write_back_email falls back to email_sequence_position + 1.
    email_number: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Email slot to fill (1-5). Set by WordPress before calling CIS.",
    )
    prospect_data: dict[str, Any] | None = Field(
        default=None,
        description="Optional pre-fetched prospect data. If None, CIS fetches from WordPress.",
    )
    callback_url: str | None = Field(
        default=None,
        description="WordPress endpoint to POST results back to. "
        "If None, results are returned synchronously.",
    )


class GenerateEmailResponse(BaseModel):
    # Response body for email generation.

    success: bool
    prospect_id: int
    campaign_id: int
    generated_email: str | None = None
    guardrail_passed: bool | None = None
    guardrail_violations: int = 0
    guardrail_suggestion: str | None = None
    selected_content_title: str | None = None
    selected_content_url: str | None = None
    intent_service_area: str | None = None
    intent_confidence: float | None = None
    analysis_source: str | None = None
    writeback_tracking_id: int | None = None
    writeback_success: bool | None = None
    processing_time_ms: int = 0
    error: str | None = None


class BatchGenerateRequest(BaseModel):
    # Request body for batch email generation.

    prospects: list[GenerateEmailRequest] = Field(
        ..., min_length=1, max_length=50,
        description="List of prospects to generate emails for",
    )
    callback_url: str | None = Field(
        default=None,
        description="WordPress endpoint to POST batch results back to.",
    )


class BatchGenerateResponse(BaseModel):
    # Response body for batch generation.

    success: bool
    total: int
    queued: int
    message: str


class HealthResponse(BaseModel):
    # Health check response.

    status: str
    version: str = "0.6.0"
    wordpress_configured: bool = False
    anthropic_configured: bool = False
    gemini_configured: bool = False


class ProcessProspectRequest(BaseModel):
    # Request body for the RTR/nightly sync trigger endpoint.

    client_id: int = Field(..., description="Client ID from cpd_clients table")
    prospect_id: int = Field(..., description="ID from rtr_prospects table")
    callback_url: str | None = Field(
        default=None,
        description="WordPress endpoint to POST results back to. "
        "If None, results are returned synchronously.",
    )


# =============================================================================
# Webhook Authentication
# =============================================================================

def _verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # Verify the incoming webhook API key matches our configured key.
    # If no key is configured on CIS side, auth is skipped (dev mode).

    if not settings.journeyos_api_key:
        return

    if x_api_key != settings.journeyos_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-API-Key header",
        )


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    # Basic health check — always returns 200 if server is running.

    return HealthResponse(
        status="ok",
        wordpress_configured=settings.has_wordpress_auth,
        anthropic_configured=settings.has_anthropic_key,
        gemini_configured=settings.has_gemini_key,
    )


@app.get("/health/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    # Readiness check — returns 503 if no LLM keys are configured.

    has_any_llm = settings.has_anthropic_key or settings.has_gemini_key

    if not has_any_llm:
        raise HTTPException(
            status_code=503,
            detail="No LLM API keys configured (need ANTHROPIC_API_KEY or GEMINI_API_KEY)",
        )

    return HealthResponse(
        status="ready",
        wordpress_configured=settings.has_wordpress_auth,
        anthropic_configured=settings.has_anthropic_key,
        gemini_configured=settings.has_gemini_key,
    )


@app.post("/webhook/generate-email", response_model=GenerateEmailResponse)
async def generate_email(
    request: GenerateEmailRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None),
) -> GenerateEmailResponse:
    # Trigger email generation for a single prospect.
    #
    # If callback_url is provided, generation runs in the background
    # and results are POSTed to WordPress. Otherwise, runs synchronously
    # and returns results in the response body.

    _verify_api_key(x_api_key)

    logger.info(
        "Email generation webhook received",
        extra={
            "prospect_id": request.prospect_id,
            "campaign_id": request.campaign_id,
            "email_number": request.email_number,
            "has_callback": request.callback_url is not None,
            "has_prospect_data": request.prospect_data is not None,
        },
    )

    if request.callback_url:
        # Async mode — queue background task and return immediately
        background_tasks.add_task(
            _generate_and_callback,
            request.prospect_id,
            request.campaign_id,
            request.prospect_data,
            request.callback_url,
            request.email_number,
        )

        return GenerateEmailResponse(
            success=True,
            prospect_id=request.prospect_id,
            campaign_id=request.campaign_id,
            error="Processing in background. Results will be POSTed to callback_url.",
        )

    # Sync mode — run pipeline and return results
    return await _run_pipeline(
        request.prospect_id,
        request.campaign_id,
        request.prospect_data,
        request.email_number,
    )


@app.post("/webhook/batch-generate", response_model=BatchGenerateResponse)
async def batch_generate(
    request: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None),
) -> BatchGenerateResponse:
    # Trigger batch email generation for multiple prospects.
    #
    # Always runs in the background. Results are POSTed to callback_url
    # for each prospect as they complete.

    _verify_api_key(x_api_key)

    callback = request.callback_url

    for prospect_req in request.prospects:
        cb = prospect_req.callback_url or callback
        background_tasks.add_task(
            _generate_and_callback,
            prospect_req.prospect_id,
            prospect_req.campaign_id,
            prospect_req.prospect_data,
            cb,
            prospect_req.email_number,
        )

    logger.info(
        "Batch generation queued",
        extra={"total": len(request.prospects)},
    )

    return BatchGenerateResponse(
        success=True,
        total=len(request.prospects),
        queued=len(request.prospects),
        message=f"Queued {len(request.prospects)} prospect(s) for email generation.",
    )


@app.post("/process-prospect", response_model=GenerateEmailResponse)
async def process_prospect(
    request: ProcessProspectRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None),
) -> GenerateEmailResponse:
    # Trigger email generation for a prospect using client_id + prospect_id.
    #
    # This is the primary entry point for RTR and nightly sync.
    # Fetches prospect from WordPress to resolve campaign_id automatically.

    _verify_api_key(x_api_key)

    logger.info(
        "Process prospect request received",
        extra={
            "client_id": request.client_id,
            "prospect_id": request.prospect_id,
            "has_callback": request.callback_url is not None,
        },
    )

    # Fetch prospect from WordPress to get campaign_id
    campaign_id = None
    prospect_data = None

    if settings.has_wordpress_auth:
        try:
            from services.wordpress_client import WordPressClient

            async with WordPressClient() as wp:
                prospect = await wp.get_prospect(request.prospect_id)

            prospect_data = prospect.model_dump()
            campaign_id = prospect.campaign_id

            logger.info(
                "Resolved campaign_id from prospect",
                extra={
                    "prospect_id": request.prospect_id,
                    "campaign_id": campaign_id,
                    "client_id": request.client_id,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to fetch prospect {request.prospect_id}: {e}",
                extra={"client_id": request.client_id},
            )
            return GenerateEmailResponse(
                success=False,
                prospect_id=request.prospect_id,
                campaign_id=0,
                error=f"Failed to fetch prospect from WordPress: {e}",
            )
    else:
        return GenerateEmailResponse(
            success=False,
            prospect_id=request.prospect_id,
            campaign_id=0,
            error="WordPress auth not configured. Cannot resolve campaign_id.",
        )

    if request.callback_url:
        # Async mode
        background_tasks.add_task(
            _generate_and_callback,
            request.prospect_id,
            campaign_id,
            prospect_data,
            request.callback_url,
            None,  # process-prospect has no email_number concept
        )

        return GenerateEmailResponse(
            success=True,
            prospect_id=request.prospect_id,
            campaign_id=campaign_id,
            error="Processing in background. Results will be POSTed to callback_url.",
        )

    # Sync mode — prospect_data already fetched, no reserved email_number
    return await _run_pipeline(
        request.prospect_id,
        campaign_id,
        prospect_data,
        None,
    )


# =============================================================================
# Pipeline Execution
# =============================================================================

async def _run_pipeline(
    prospect_id: int,
    campaign_id: int,
    prospect_data: dict[str, Any] | None = None,
    email_number: int | None = None,
) -> GenerateEmailResponse:
    # Run the full LangGraph pipeline and build a response.

    start = time.monotonic()

    try:
        result = await run_email_generation(
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            prospect_data=prospect_data,
            email_number=email_number,
        )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Extract results from final state
        guardrail = result.get("guardrail_result")
        selected = result.get("selected_content")
        intent = result.get("intent_profile")
        writeback = result.get("writeback_result")

        return GenerateEmailResponse(
            success=result.get("error") is None,
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            generated_email=result.get("generated_email"),
            guardrail_passed=guardrail.passed if guardrail else None,
            guardrail_violations=guardrail.violation_count if guardrail else 0,
            guardrail_suggestion=guardrail.suggestion if guardrail else None,
            selected_content_title=selected.title if selected else None,
            selected_content_url=selected.url if selected else None,
            intent_service_area=intent.service_area if intent else None,
            intent_confidence=intent.confidence if intent else None,
            analysis_source=intent.analysis_source if intent else None,
            processing_time_ms=elapsed_ms,
            writeback_tracking_id=(
                writeback.get("email_tracking_id") if writeback and "email_tracking_id" in writeback else None
            ),
            writeback_success=(
                writeback is not None and "error" not in writeback
            ) if writeback else None,
            error=result.get("error"),
        )

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception(f"Pipeline failed for prospect {prospect_id}")

        return GenerateEmailResponse(
            success=False,
            prospect_id=prospect_id,
            campaign_id=campaign_id,
            processing_time_ms=elapsed_ms,
            error=str(e),
        )


# =============================================================================
# Callback to WordPress
# =============================================================================

async def _generate_and_callback(
    prospect_id: int,
    campaign_id: int,
    prospect_data: dict[str, Any] | None,
    callback_url: str | None,
    email_number: int | None = None,
) -> None:
    # Run pipeline and POST results to WordPress callback endpoint.

    response = await _run_pipeline(prospect_id, campaign_id, prospect_data, email_number)

    if not callback_url:
        logger.warning(
            "No callback_url — results discarded",
            extra={"prospect_id": prospect_id},
        )
        return

    try:
        payload = response.model_dump()

        # Build auth for the callback (WordPress Application Passwords)
        auth = None
        if settings.has_wordpress_auth:
            auth = httpx.BasicAuth(
                username=settings.wordpress_app_user,
                password=settings.wordpress_app_password,
            )

        async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
            cb_response = await client.post(
                callback_url,
                json=payload,
                auth=auth,
                headers={"Content-Type": "application/json"},
            )
            cb_response.raise_for_status()

        logger.info(
            "Callback to WordPress succeeded",
            extra={
                "prospect_id": prospect_id,
                "callback_url": callback_url,
                "status_code": cb_response.status_code,
            },
        )

    except Exception as e:
        logger.error(
            f"Callback to WordPress failed: {e}",
            extra={
                "prospect_id": prospect_id,
                "callback_url": callback_url,
            },
        )


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
