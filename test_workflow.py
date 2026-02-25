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
    # Test synchronous graph execution
    from models.state import create_initial_state, ProspectIntent, RankedAsset
    from graphs.email_generation import email_generation_graph

    print("\n" + "=" * 60)
    print("TEST: Synchronous Graph Execution")
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
    # Test async workflow execution
    from graphs.email_generation import run_email_generation

    print("\n" + "=" * 60)
    print("TEST: Async Workflow Execution")
    print("=" * 60)

    result = await run_email_generation(prospect_id=99, campaign_id=2)

    selected = result.get("selected_content")
    if selected:
        print(f"\n\u2713 Async execution complete!")
        print(f"  Recommendation: {selected.title}")
        return True

    print("\n\u2717 Async execution failed")
    return False


def main() -> int:
    # Run all tests
    print("\n" + "#" * 60)
    print("# Content Intelligence System")
    print("# Workflow Test Suite")
    print("#" * 60)

    # Test 1: Sync execution
    sync_ok = test_sync_execution()

    # Test 2: Async execution
    async_ok = asyncio.run(test_async_execution())

    # Summary
    print("\n" + "#" * 60)
    print("# Test Summary")
    print("#" * 60)
    print(f"  Sync Execution:  {'\u2713 PASS' if sync_ok else '\u2717 FAIL'}")
    print(f"  Async Execution: {'\u2713 PASS' if async_ok else '\u2717 FAIL'}")
    print("#" * 60 + "\n")

    return 0 if (sync_ok and async_ok) else 1


if __name__ == "__main__":
    sys.exit(main())