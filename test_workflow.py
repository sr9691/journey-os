#!/usr/bin/env python3
# =============================================================================
# Test script to verify email generation graph execution
# =============================================================================
#
# Run from project root:
#     python test_workflow.py
#
# Expected output:
# - Graph executes successfully
# - Intent profile is extracted (Pydantic ProspectIntent)
# - Assets are ranked (Pydantic RankedAsset list)
# - Top recommendation is displayed
#
# Phase 1: Added WordPress fetch test
# =============================================================================

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging to see agent activity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def test_sync_execution() -> bool:
    # Test synchronous graph execution with pre-provided data
    from models.state import create_initial_state, ProspectIntent, RankedAsset
    from graphs.email_generation import email_generation_graph

    print("\n" + "=" * 60)
    print("TEST: Synchronous Graph Execution (pre-provided data)")
    print("=" * 60)

    # Create initial state with test data
    state = create_initial_state(
        prospect_id=45,
        campaign_id=1,
        prospect_data={
            "id": 45,
            "campaign_id": 1,
            "current_room": "problem",
            "lead_score": 35,
            "company_name": "Acme Health Systems",
            "contact_name": "Sarah Johnson",
            "job_title": "VP of Operations",
            "industry": "Healthcare",
            "employee_count": "1001-5000",
        },
    )

    print(f"\nInput:")
    print(f"  Prospect ID: {state['prospect_id']}")
    print(f"  Company: {state['prospect_data']['company_name']}")
    print(f"  Industry: {state['prospect_data']['industry']}")
    print(f"  Current Room: {state['prospect_data']['current_room']}")

    # Run the graph
    print("\nExecuting graph...")
    result = email_generation_graph.invoke(state)

    # Display results
    print("\n" + "-" * 40)
    print("Results:")
    print("-" * 40)

    intent = result.get("intent_profile")
    if intent:
        # intent is now a Pydantic ProspectIntent model
        print(f"\nIntent Profile (ProspectIntent):")
        print(f"  Service Area: {intent.service_area}")
        print(f"  Confidence: {intent.confidence:.0%}")
        print(f"  Pain Points:")
        for pp in intent.pain_points:
            print(f"    - {pp}")

    ranked = result.get("ranked_assets", [])
    print(f"\nRanked Assets: {len(ranked)} found")
    for i, asset in enumerate(ranked, 1):
        # asset is now a Pydantic RankedAsset model
        print(f"  {i}. [{asset.room.upper()}] {asset.title}")
        print(f"     Score: {asset.score} | URL: {asset.url}")

    selected = result.get("selected_content")
    if selected:
        print(f"\n\u2713 Top Recommendation: {selected.title}")

    # Check for errors
    if result.get("error"):
        print(f"\n\u2717 Error: {result['error']}")
        return False

    print("\n" + "=" * 60)
    print("\u2713 Graph executed successfully!")
    print("=" * 60)
    return True


async def test_async_execution() -> bool:
    # Test async workflow execution (uses mock data fallback)
    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("TEST: Async Workflow Execution (auto-fetch or mock fallback)")
    print("=" * 60)

    result = await run_email_generation(prospect_id=99, campaign_id=2)

    # Show what data source was used
    prospect_data = result.get("prospect_data", {})
    company = prospect_data.get("company_name", "Unknown")
    room = prospect_data.get("current_room", "Unknown")
    industry = prospect_data.get("industry", "Unknown")

    print(f"\n  Data Source: {'WordPress' if company != 'Acme Health Systems' else 'Mock fallback'}")
    print(f"  Company: {company}")
    print(f"  Room: {room}")
    print(f"  Industry: {industry}")

    selected = result.get("selected_content")
    if selected:
        print(f"\n\u2713 Async execution complete!")
        print(f"  Recommendation: {selected.title}")
        return True

    print("\n\u2717 Async execution failed")
    return False


async def test_wordpress_fetch() -> bool:
    # Test WordPress data fetching directly
    # Only runs if WORDPRESS_APP_USER and WORDPRESS_APP_PASSWORD are set
    from config.settings import settings

    print("\n" + "=" * 60)
    print("TEST: WordPress Data Fetch")
    print("=" * 60)

    if not settings.has_wordpress_auth:
        print("\n  SKIPPED: No WordPress Application Password configured")
        print("  Set WORDPRESS_APP_USER and WORDPRESS_APP_PASSWORD in .env")
        print("=" * 60)
        return True  # Not a failure, just skipped

    print(f"\n  WordPress URL: {settings.wordpress_base_url}")
    print(f"  Auth User: {settings.wordpress_app_user}")

    try:
        from services.wordpress_client import WordPressClient

        async with WordPressClient() as wp:
            # Try to list prospects first (less likely to fail with bad ID)
            prospects = await wp.list_prospects(per_page=1)

            if prospects:
                prospect = prospects[0]
                print(f"\n  Found prospect:")
                print(f"    ID: {prospect.id}")
                print(f"    Company: {prospect.company_name}")
                print(f"    Room: {prospect.current_room}")
                print(f"    Lead Score: {prospect.lead_score}")
                print(f"    Industry: {prospect.industry}")
                print(f"    Job Title: {prospect.job_title}")

                # Now test the full workflow with this real prospect
                print(f"\n  Running full workflow with prospect {prospect.id}...")
                from graphs.email_generation import run_email_generation

                result = await run_email_generation(
                    prospect_id=prospect.id,
                    campaign_id=prospect.campaign_id,
                )

                selected = result.get("selected_content")
                if selected:
                    print(f"  \u2713 Recommendation: {selected.title}")
                elif result.get("error"):
                    print(f"  \u2717 Error: {result['error']}")
                else:
                    print(f"  \u2713 Workflow completed (no content matched)")
            else:
                print("\n  No prospects found in WordPress")

        print("\n" + "=" * 60)
        print("\u2713 WordPress fetch test complete!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n\u2717 WordPress fetch failed: {e}")
        print("=" * 60)
        return False


def main() -> int:
    # Run all tests
    print("\n" + "#" * 60)
    print("# Content Intelligence System")
    print("# Workflow Test Suite")
    print("#" * 60)

    # Test 1: Sync execution with pre-provided data
    sync_ok = test_sync_execution()

    # Test 2: Async execution (auto-fetch or mock fallback)
    async_ok = asyncio.run(test_async_execution())

    # Test 3: WordPress fetch (skipped if no auth configured)
    wp_ok = asyncio.run(test_wordpress_fetch())

    # Summary
    print("\n" + "#" * 60)
    print("# Test Summary")
    print("#" * 60)
    print(f"  Sync Execution:   {'\u2713 PASS' if sync_ok else '\u2717 FAIL'}")
    print(f"  Async Execution:  {'\u2713 PASS' if async_ok else '\u2717 FAIL'}")
    print(f"  WordPress Fetch:  {'\u2713 PASS' if wp_ok else '\u2717 FAIL'}")
    print("#" * 60 + "\n")

    return 0 if (sync_ok and async_ok and wp_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
