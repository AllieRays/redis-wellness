#!/usr/bin/env python3
"""
Populate Semantic Memory with Verified Health Facts.

This script loads the verified health knowledge base into Redis.
Run this during application startup or manually to refresh semantic memory.

Safety Features:
- Only loads facts from verified knowledge base
- Includes source attribution for every fact
- Tracks confidence levels (high/medium)
- Skips duplicates if memory already populated
- Provides detailed logging of what was loaded
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# ruff: noqa: E402
from src.data.semantic_knowledge_base import (
    MEDICAL_DISCLAIMER,
    get_verified_health_facts,
)
from src.services.semantic_memory_manager import get_semantic_memory_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def populate_semantic_memory(
    force_refresh: bool = False, high_confidence_only: bool = False
) -> dict[str, any]:
    """
    Populate semantic memory with verified health facts.

    Args:
        force_refresh: If True, clears existing semantic memory before populating
        high_confidence_only: If True, only loads high-confidence facts

    Returns:
        Dict with statistics about the population process
    """
    logger.info("=" * 70)
    logger.info("SEMANTIC MEMORY POPULATION - Verified Health Knowledge")
    logger.info("=" * 70)

    # Get semantic memory manager
    semantic_manager = get_semantic_memory_manager()

    # Get verified facts
    all_facts = get_verified_health_facts()

    # Filter by confidence if requested
    if high_confidence_only:
        facts_to_load = [f for f in all_facts if f.get("confidence") == "high"]
        logger.info(
            f"Loading {len(facts_to_load)} HIGH-CONFIDENCE facts only "
            f"(skipping {len(all_facts) - len(facts_to_load)} medium-confidence facts)"
        )
    else:
        facts_to_load = all_facts
        logger.info(
            f"Loading {len(facts_to_load)} verified facts (all confidence levels)"
        )

    # Clear existing semantic memory if force refresh
    if force_refresh:
        logger.warning("Force refresh enabled - clearing existing semantic memory...")
        await semantic_manager.clear_semantic_knowledge()
        logger.info("Existing semantic memory cleared")

    # Statistics tracking
    stats = {
        "total_facts": len(facts_to_load),
        "stored_successfully": 0,
        "failed": 0,
        "categories": {},
        "fact_types": {},
        "confidence_levels": {"high": 0, "medium": 0},
        "sources": set(),
    }

    # Load facts
    logger.info("\nLoading facts into semantic memory...")
    for i, fact_data in enumerate(facts_to_load, 1):
        try:
            # Extract fact details
            fact = fact_data["fact"]
            fact_type = fact_data["fact_type"]
            category = fact_data["category"]
            context = fact_data.get("context", "")
            source = fact_data.get("source", "unknown")
            confidence = fact_data.get("confidence", "medium")

            # Store in semantic memory
            success = await semantic_manager.store_semantic_fact(
                fact=fact,
                fact_type=fact_type,
                category=category,
                context=context,
                source=source,
                metadata={
                    "confidence": confidence,
                    "last_verified": fact_data.get("last_verified", "unknown"),
                },
            )

            if success:
                stats["stored_successfully"] += 1

                # Track by category
                if category not in stats["categories"]:
                    stats["categories"][category] = 0
                stats["categories"][category] += 1

                # Track by fact type
                if fact_type not in stats["fact_types"]:
                    stats["fact_types"][fact_type] = 0
                stats["fact_types"][fact_type] += 1

                # Track confidence levels
                stats["confidence_levels"][confidence] += 1

                # Track sources
                stats["sources"].add(source)

                logger.debug(
                    f"[{i}/{len(facts_to_load)}] Stored: {fact[:60]}... [{category}/{fact_type}]"
                )
            else:
                stats["failed"] += 1
                logger.warning(f"Failed to store fact: {fact[:60]}...")

        except Exception as e:
            stats["failed"] += 1
            logger.error(f"Error storing fact {i}: {e}", exc_info=True)

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("SEMANTIC MEMORY POPULATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total facts: {stats['total_facts']}")
    logger.info(f"Stored successfully: {stats['stored_successfully']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(
        f"Success rate: {(stats['stored_successfully'] / stats['total_facts'] * 100):.1f}%"
    )

    logger.info("\nBreakdown by Category:")
    for category, count in sorted(stats["categories"].items()):
        logger.info(f"  - {category}: {count} facts")

    logger.info("\nBreakdown by Fact Type:")
    for fact_type, count in sorted(stats["fact_types"].items()):
        logger.info(f"  - {fact_type}: {count} facts")

    logger.info("\nConfidence Levels:")
    logger.info(f"  - High confidence: {stats['confidence_levels']['high']} facts")
    logger.info(f"  - Medium confidence: {stats['confidence_levels']['medium']} facts")

    logger.info(f"\nAuthoritative Sources Used ({len(stats['sources'])}):")
    for source in sorted(stats["sources"]):
        logger.info(f"  - {source}")

    logger.info("\n" + "=" * 70)
    logger.info("MEDICAL DISCLAIMER")
    logger.info("=" * 70)
    logger.info(MEDICAL_DISCLAIMER)

    return stats


async def test_semantic_retrieval() -> None:
    """
    Test semantic memory retrieval with sample queries.

    This ensures the populated facts can be retrieved correctly.
    """
    logger.info("\n" + "=" * 70)
    logger.info("TESTING SEMANTIC RETRIEVAL")
    logger.info("=" * 70)

    semantic_manager = get_semantic_memory_manager()

    test_queries = [
        ("What is VO2 max?", ["metrics"]),
        ("heart rate zones", ["cardio"]),
        ("How much exercise should I do?", ["exercise"]),
        ("What is BMI?", ["metrics"]),
        ("sleep recommendations", ["sleep"]),
    ]

    for query, categories in test_queries:
        logger.info(f"\nQuery: '{query}' (categories: {categories})")
        result = await semantic_manager.retrieve_semantic_knowledge(
            query=query, categories=categories, top_k=2
        )

        if result.get("hits", 0) > 0:
            logger.info(f"✅ Found {result['hits']} relevant facts")
            logger.debug(f"Context:\n{result.get('context', 'N/A')[:200]}...")
        else:
            logger.warning("❌ No facts found")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Populate semantic memory with verified health facts"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Clear existing semantic memory before populating",
    )
    parser.add_argument(
        "--high-confidence-only",
        action="store_true",
        help="Only load high-confidence facts",
    )
    parser.add_argument(
        "--test", action="store_true", help="Run retrieval tests after populating"
    )

    args = parser.parse_args()

    # Run population
    try:
        stats = asyncio.run(
            populate_semantic_memory(
                force_refresh=args.force_refresh,
                high_confidence_only=args.high_confidence_only,
            )
        )

        # Run tests if requested
        if args.test:
            asyncio.run(test_semantic_retrieval())

        # Exit with appropriate code
        if stats["failed"] > 0:
            logger.warning(
                f"Completed with {stats['failed']} failures out of {stats['total_facts']} facts"
            )
            sys.exit(1)
        else:
            logger.info("✅ All facts loaded successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
