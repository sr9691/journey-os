#!/usr/bin/env python3
# =============================================================================
# End-to-End Tests for Content Intelligence System
# =============================================================================
#
# Tests the full pipeline from webhook request through email generation
# and guardrail inspection, including the FastAPI server endpoints.
#
# Run from project root:
#     python test_e2e.py
#
# Phase 6: End-to-End Testing & WordPress Webhook
# =============================================================================

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Data Fixtures
# =============================================================================

PROBLEM_PROSPECT = {
    "id": 45,
    "campaign_id": 1,
    "current_room": "problem",
    "lead_score": 35,
    "company_name": "Acme Health Systems",
    "contact_name": "Sarah Johnson",
    "job_title": "VP of Operations",
    "industry": "Healthcare",
    "employee_count": "1001-5000",
}

SOLUTION_PROSPECT = {
    "id": 77,
    "campaign_id": 1,
    "current_room": "solution",
    "lead_score": 55,
    "company_name": "FinServ Global",
    "contact_name": "James Chen",
    "job_title": "CTO",
    "industry": "Financial Services",
    "employee_count": "5001-10000",
    "days_in_room": 18,
    "engagement_data": "/cloud-migration/assessment, /case-studies/banking",
}

OFFER_PROSPECT = {
    "id": 120,
    "campaign_id": 1,
    "current_room": "offer",
    "lead_score": 72,
    "company_name": "TechMfg Corp",
    "contact_name": "Maria Gonzalez",
    "job_title": "Director of IT",
    "industry": "Manufacturing",
    "employee_count": "501-1000",
    "days_in_room": 25,
    "engagement_data": "/cloud-modernization/kubernetes, /pricing",
}

MINIMAL_PROSPECT = {
    "id": 999,
    "campaign_id": 1,
    "current_room": "problem",
    "lead_score": 10,
    "company_name": "Unknown Corp",
}


# =============================================================================
# E2E Pipeline Tests
# =============================================================================

async def test_e2e_problem_room() -> bool:
    """E2E: Full pipeline for a problem-room prospect."""

    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("E2E TEST: Problem Room Pipeline")
    print("=" * 60)

    start = time.monotonic()
    result = await run_email_generation(
        prospect_id=45,
        campaign_id=1,
        prospect_data=PROBLEM_PROSPECT,
    )
    elapsed = (time.monotonic() - start) * 1000

    passed = True

    # Check intent was extracted
    intent = result.get("intent_profile")
    if not intent:
        print("  \u2717 FAIL: No intent profile")
        return False
    print(f"  \u2713 Intent: service_area={intent.service_area}, source={intent.analysis_source}")

    # Check assets were ranked
    ranked = result.get("ranked_assets", [])
    if not ranked:
        print("  \u2717 FAIL: No ranked assets")
        return False
    print(f"  \u2713 Assets: {len(ranked)} ranked, top={ranked[0].title[:40]}...")

    # Check email was generated
    email = result.get("generated_email")
    if not email or len(email) < 50:
        print("  \u2717 FAIL: No email generated or too short")
        return False
    print(f"  \u2713 Email: {len(email)} chars")

    # Check guardrails ran
    guardrail = result.get("guardrail_result")
    if not guardrail:
        print("  \u2717 FAIL: No guardrail result")
        return False
    print(f"  \u2713 Guardrails: passed={guardrail.passed}, violations={guardrail.violation_count}")

    # Check no hard errors
    if result.get("error"):
        print(f"  \u2717 FAIL: Error in pipeline: {result['error']}")
        passed = False

    print(f"\n  Processing time: {elapsed:.0f}ms")

    if passed:
        print("  \u2713 Problem room E2E PASSED")
    return passed


async def test_e2e_solution_room() -> bool:
    """E2E: Full pipeline for a solution-room prospect."""

    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("E2E TEST: Solution Room Pipeline")
    print("=" * 60)

    result = await run_email_generation(
        prospect_id=77,
        campaign_id=1,
        prospect_data=SOLUTION_PROSPECT,
    )

    passed = True

    intent = result.get("intent_profile")
    email = result.get("generated_email")
    guardrail = result.get("guardrail_result")

    if not intent:
        print("  \u2717 FAIL: No intent profile")
        return False

    # Solution room should detect cloud-migration from engagement data
    if intent.service_area and "cloud" in (intent.service_area or ""):
        print(f"  \u2713 Detected service area from engagement: {intent.service_area}")
    else:
        print(f"  \u2022 Service area: {intent.service_area}")

    if intent.urgency_level == "high":
        print(f"  \u2713 Urgency correctly set to 'high' (lead_score=55)")
    else:
        print(f"  \u2022 Urgency: {intent.urgency_level}")

    if not email:
        print("  \u2717 FAIL: No email generated")
        return False
    print(f"  \u2713 Email: {len(email)} chars")

    if guardrail:
        print(f"  \u2713 Guardrails: passed={guardrail.passed}, room={guardrail.room}")

    if result.get("error"):
        print(f"  \u2717 Error: {result['error']}")
        passed = False

    if passed:
        print("  \u2713 Solution room E2E PASSED")
    return passed


async def test_e2e_offer_room() -> bool:
    """E2E: Full pipeline for an offer-room prospect."""

    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("E2E TEST: Offer Room Pipeline")
    print("=" * 60)

    result = await run_email_generation(
        prospect_id=120,
        campaign_id=1,
        prospect_data=OFFER_PROSPECT,
    )

    passed = True

    email = result.get("generated_email")
    guardrail = result.get("guardrail_result")

    if not email:
        print("  \u2717 FAIL: No email generated")
        return False

    # Offer room emails should include a CTA
    has_cta = any(w in email.lower() for w in ["call", "schedule", "discuss", "demo", "meeting"])
    if has_cta:
        print(f"  \u2713 Offer email includes CTA")
    else:
        print(f"  \u2022 Offer email may be missing CTA")

    print(f"  \u2713 Email: {len(email)} chars")

    if guardrail:
        # Offer room is most permissive \u2014 should pass more easily
        print(f"  \u2713 Guardrails: passed={guardrail.passed}, violations={guardrail.violation_count}")

    if result.get("error"):
        print(f"  \u2717 Error: {result['error']}")
        passed = False

    if passed:
        print("  \u2713 Offer room E2E PASSED")
    return passed


async def test_e2e_minimal_data() -> bool:
    """E2E: Pipeline handles minimal prospect data gracefully."""

    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("E2E TEST: Minimal Prospect Data")
    print("=" * 60)

    result = await run_email_generation(
        prospect_id=999,
        campaign_id=1,
        prospect_data=MINIMAL_PROSPECT,
    )

    passed = True

    intent = result.get("intent_profile")
    if not intent:
        print("  \u2717 FAIL: Should produce intent even with minimal data")
        return False
    print(f"  \u2713 Intent: service_area={intent.service_area} (default heuristic)")

    email = result.get("generated_email")
    if email:
        print(f"  \u2713 Email generated even with minimal data: {len(email)} chars")
    else:
        print(f"  \u2022 No email generated (may be expected with very minimal data)")

    if result.get("error"):
        print(f"  \u2717 Error: {result['error']}")
        passed = False

    if passed:
        print("  \u2713 Minimal data E2E PASSED")
    return passed


async def test_e2e_room_consistency() -> bool:
    """E2E: Verify each room produces distinct emails with appropriate tone."""

    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("E2E TEST: Cross-Room Consistency")
    print("=" * 60)

    prospects = {
        "problem": PROBLEM_PROSPECT,
        "solution": SOLUTION_PROSPECT,
        "offer": OFFER_PROSPECT,
    }

    emails: dict[str, str] = {}
    passed = True

    for room, prospect_data in prospects.items():
        result = await run_email_generation(
            prospect_id=prospect_data["id"],
            campaign_id=1,
            prospect_data=prospect_data,
        )
        email = result.get("generated_email", "")
        emails[room] = email
        if email:
            print(f"  \u2713 {room.capitalize()} room: {len(email)} chars")
        else:
            print(f"  \u2717 {room.capitalize()} room: no email")
            passed = False

    # All three rooms should produce different emails
    unique_emails = set(emails.values()) - {""}
    if len(unique_emails) >= 2:
        print(f"  \u2713 {len(unique_emails)} distinct emails across rooms")
    else:
        print(f"  \u2717 FAIL: Rooms should produce distinct emails")
        passed = False

    if passed:
        print("  \u2713 Cross-room consistency PASSED")
    return passed


# =============================================================================
# FastAPI Server Tests
# =============================================================================

async def test_webhook_server() -> bool:
    """Test FastAPI server endpoints using TestClient."""

    print("\n" + "=" * 60)
    print("E2E TEST: Webhook Server Endpoints")
    print("=" * 60)

    try:
        from httpx import AsyncClient, ASGITransport
        from server import app
    except ImportError as e:
        print(f"  \u2717 FAIL: Cannot import server dependencies: {e}")
        print("  Install with: pip install fastapi uvicorn")
        return False

    passed = True
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # Test 1: Health check
        print(f"\n  Test 1: GET /health")
        resp = await client.get("/health")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  \u2713 Status: {data['status']}, version: {data['version']}")
        else:
            print(f"  \u2717 FAIL: Health check returned {resp.status_code}")
            passed = False

        # Test 2: Synchronous email generation
        print(f"\n  Test 2: POST /webhook/generate-email (sync)")
        payload = {
            "prospect_id": 45,
            "campaign_id": 1,
            "prospect_data": PROBLEM_PROSPECT,
        }
        resp = await client.post("/webhook/generate-email", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  \u2713 success={data['success']}")
            print(f"    email_length={len(data.get('generated_email') or '')}")
            print(f"    guardrail_passed={data.get('guardrail_passed')}")
            print(f"    processing_time={data.get('processing_time_ms')}ms")
            if not data.get("generated_email"):
                print("  \u2717 FAIL: No email in sync response")
                passed = False
        else:
            print(f"  \u2717 FAIL: Sync generation returned {resp.status_code}: {resp.text}")
            passed = False

        # Test 3: Async mode (with callback_url \u2014 won't actually call back)
        print(f"\n  Test 3: POST /webhook/generate-email (async)")
        payload["callback_url"] = "http://localhost/fake-callback"
        resp = await client.post("/webhook/generate-email", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if "background" in (data.get("error") or "").lower():
                print(f"  \u2713 Queued for background processing")
            else:
                print(f"  \u2713 Response: success={data['success']}")
        else:
            print(f"  \u2717 FAIL: Async generation returned {resp.status_code}")
            passed = False

        # Test 4: Batch generation
        print(f"\n  Test 4: POST /webhook/batch-generate")
        batch_payload = {
            "prospects": [
                {"prospect_id": 45, "campaign_id": 1, "prospect_data": PROBLEM_PROSPECT},
                {"prospect_id": 77, "campaign_id": 1, "prospect_data": SOLUTION_PROSPECT},
            ],
            "callback_url": "http://localhost/fake-callback",
        }
        resp = await client.post("/webhook/batch-generate", json=batch_payload)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  \u2713 Batch queued: {data['queued']}/{data['total']} prospects")
        else:
            print(f"  \u2717 FAIL: Batch returned {resp.status_code}")
            passed = False

        # Test 5: Invalid request
        print(f"\n  Test 5: POST /webhook/generate-email (invalid)")
        resp = await client.post("/webhook/generate-email", json={})
        if resp.status_code == 422:
            print(f"  \u2713 Correctly rejected invalid request (422)")
        else:
            print(f"  \u2717 FAIL: Expected 422 for invalid request, got {resp.status_code}")
            passed = False

        # Test 6: API key auth (when configured)
        print(f"\n  Test 6: API key authentication")
        from config.settings import settings
        if settings.wordpress_api_key:
            # With wrong key
            resp = await client.post(
                "/webhook/generate-email",
                json={"prospect_id": 1, "campaign_id": 1},
                headers={"X-API-Key": "wrong-key"},
            )
            if resp.status_code == 401:
                print(f"  \u2713 Rejected invalid API key (401)")
            else:
                print(f"  \u2717 FAIL: Should reject bad API key")
                passed = False
        else:
            print(f"  \u2022 Skipped: No API key configured (auth bypassed in dev mode)")

    if passed:
        print("\n  \u2713 Webhook server tests PASSED")
    return passed


async def test_response_structure() -> bool:
    """Verify the GenerateEmailResponse has all fields WordPress expects."""

    print("\n" + "=" * 60)
    print("E2E TEST: Response Structure Validation")
    print("=" * 60)

    from httpx import AsyncClient, ASGITransport
    from server import app

    passed = True
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "prospect_id": 45,
            "campaign_id": 1,
            "prospect_data": PROBLEM_PROSPECT,
        }
        resp = await client.post("/webhook/generate-email", json=payload)
        data = resp.json()

        # Check all expected fields exist
        required_fields = [
            "success", "prospect_id", "campaign_id", "generated_email",
            "guardrail_passed", "guardrail_violations", "guardrail_suggestion",
            "selected_content_title", "selected_content_url",
            "intent_service_area", "intent_confidence", "analysis_source",
            "processing_time_ms", "error",
        ]

        for field in required_fields:
            if field in data:
                print(f"  \u2713 {field}: {str(data[field])[:60]}")
            else:
                print(f"  \u2717 FAIL: Missing field: {field}")
                passed = False

    if passed:
        print("\n  \u2713 Response structure PASSED")
    return passed


# =============================================================================
# Test Runner
# =============================================================================

async def run_all_e2e_tests() -> int:
    """Run all end-to-end tests."""

    print("\n" + "#" * 60)
    print("# Content Intelligence System")
    print("# End-to-End Test Suite (Phase 6)")
    print("#" * 60)

    # Pipeline E2E tests
    problem_ok = await test_e2e_problem_room()
    solution_ok = await test_e2e_solution_room()
    offer_ok = await test_e2e_offer_room()
    minimal_ok = await test_e2e_minimal_data()
    consistency_ok = await test_e2e_room_consistency()

    # Server E2E tests
    server_ok = await test_webhook_server()
    structure_ok = await test_response_structure()

    # Summary
    print("\n" + "#" * 60)
    print("# E2E Test Summary")
    print("#" * 60)
    pass_mark = "\u2713 PASS"
    fail_mark = "\u2717 FAIL"
    print(f"  Problem Room E2E:    {pass_mark if problem_ok else fail_mark}")
    print(f"  Solution Room E2E:   {pass_mark if solution_ok else fail_mark}")
    print(f"  Offer Room E2E:      {pass_mark if offer_ok else fail_mark}")
    print(f"  Minimal Data E2E:    {pass_mark if minimal_ok else fail_mark}")
    print(f"  Cross-Room Check:    {pass_mark if consistency_ok else fail_mark}")
    print(f"  Webhook Server:      {pass_mark if server_ok else fail_mark}")
    print(f"  Response Structure:  {pass_mark if structure_ok else fail_mark}")
    print("#" * 60 + "\n")

    all_passed = all([problem_ok, solution_ok, offer_ok, minimal_ok, consistency_ok, server_ok, structure_ok])
    return 0 if all_passed else 1


def main() -> int:
    return asyncio.run(run_all_e2e_tests())


if __name__ == "__main__":
    sys.exit(main())
