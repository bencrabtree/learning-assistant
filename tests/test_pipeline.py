#!/usr/bin/env python3
"""
Test Script - Verify Full Pipeline

This script tests the complete ArXiv Learning Assistant pipeline:
1. Database connection
2. Discovery agent
3. Reader agent
4. Explainer agent
5. Curator agent
6. LangGraph workflow

Run this to verify everything is working!

Usage:
    python test_pipeline.py
"""

import sys
from loguru import logger

# Configure simple logging for tests
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


def test_database():
    """Test database connection and initialization."""
    logger.info("=" * 60)
    logger.info("TEST 1: Database Connection")
    logger.info("=" * 60)

    try:
        from src.database import check_database_connection, get_database_stats

        if not check_database_connection():
            logger.error("❌ Database connection failed!")
            return False

        stats = get_database_stats()
        logger.info(f"✅ Database connected! Stats: {stats}")
        return True

    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Configuration")
    logger.info("=" * 60)

    try:
        from src.config import settings, get_research_interests_list

        logger.info(f"Research interests: {get_research_interests_list()}")
        logger.info(f"Reader model: {settings.reader_model}")
        logger.info(f"Explainer model: {settings.explainer_model}")

        if not settings.anthropic_api_key or settings.anthropic_api_key.startswith("sk-ant-api03-your"):
            logger.warning("⚠️  API key not set in .env!")
            logger.warning("   Add your key to .env: ANTHROPIC_API_KEY=sk-ant-api03-...")
            return False

        logger.info("✅ Configuration loaded!")
        return True

    except Exception as e:
        logger.error(f"❌ Config test failed: {e}")
        return False


def test_claude_client():
    """Test Claude API client."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Claude API Client")
    logger.info("=" * 60)

    try:
        from src.services.claude_client import get_claude_client

        client = get_claude_client()

        # Simple test
        logger.info("Testing simple chat...")
        response = client.chat(
            prompt="Say 'Hello' in one word.",
            temperature=0,
        )
        logger.info(f"Response: {response}")

        # JSON test
        logger.info("Testing JSON mode...")
        response = client.chat_json(
            prompt='Return this JSON: {"test": "success"}',
            temperature=0,
        )
        logger.info(f"JSON Response: {response}")

        logger.info("✅ Claude API working!")
        return True

    except Exception as e:
        logger.error(f"❌ Claude API test failed: {e}")
        logger.error("   Make sure ANTHROPIC_API_KEY is set in .env")
        return False


def test_discovery():
    """Test discovery agent (without actually calling arXiv)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Discovery Agent (Structure)")
    logger.info("=" * 60)

    try:
        from src.agents.discovery import (
            build_arxiv_query,
            save_papers_to_db,
        )

        # Test query building
        query = build_arxiv_query(["cs.AI", "cs.LG"], days_back=1)
        logger.info(f"Query: {query}")

        # Test paper saving with mock data
        from datetime import datetime
        from src.models.paper import Paper

        mock_papers = [{
            "arxiv_id": "test.12345",
            "title": "Test Paper",
            "abstract": "This is a test",
            "authors": ["Test Author"],
            "published_date": datetime.now(),
            "categories": ["cs.AI"],
            "pdf_url": "https://arxiv.org/pdf/test.12345",
            "abstract_url": "https://arxiv.org/abs/test.12345",
            "discovered_by": "test",
        }]

        # Note: This will actually save to DB if you want to test that
        # num_saved = save_papers_to_db(mock_papers)
        # logger.info(f"Saved {num_saved} test papers")

        logger.info("✅ Discovery agent structure valid!")
        return True

    except Exception as e:
        logger.error(f"❌ Discovery test failed: {e}")
        return False


def test_agents():
    """Test agent initialization."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Agent Initialization")
    logger.info("=" * 60)

    try:
        from src.agents.reader import ReaderAgent
        from src.agents.explainer import ExplainerAgent
        from src.agents.curator import CuratorAgent

        reader = ReaderAgent()
        logger.info("✅ Reader agent initialized")

        explainer = ExplainerAgent()
        logger.info("✅ Explainer agent initialized")

        curator = CuratorAgent()
        logger.info("✅ Curator agent initialized")

        return True

    except Exception as e:
        logger.error(f"❌ Agent initialization failed: {e}")
        return False


def test_langgraph():
    """Test LangGraph workflow construction."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: LangGraph Workflow")
    logger.info("=" * 60)

    try:
        from src.graph import create_workflow

        workflow = create_workflow()
        logger.info("✅ LangGraph workflow created!")

        # Show the flow
        logger.info("Flow: START → Discovery → Reader → Explainer → END")

        return True

    except Exception as e:
        logger.error(f"❌ LangGraph test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("\n🧪 TESTING ARXIV LEARNING ASSISTANT\n")

    tests = [
        ("Database", test_database),
        ("Configuration", test_config),
        ("Claude API", test_claude_client),
        ("Discovery Agent", test_discovery),
        ("Agent Initialization", test_agents),
        ("LangGraph Workflow", test_langgraph),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {name}")

    logger.info("=" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed! Your setup is ready to go!")
        logger.info("\nNext steps:")
        logger.info("  1. Make sure API key is in .env")
        logger.info("  2. Run: python main.py --discover --days 1 --analyze --max-papers 2")
        logger.info("  3. Check: python main.py --stats")
        return 0
    else:
        logger.error("\n⚠️  Some tests failed. Check the errors above.")
        logger.error("Most common issue: Missing ANTHROPIC_API_KEY in .env")
        return 1


if __name__ == "__main__":
    sys.exit(main())
