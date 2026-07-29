"""Tests for agent session state clearing between reviews (issue #43).

Covers agent/orchestrator.py + agent/memory/session_store.py: after a
portfolio is updated, a re-review should not reuse stale tool results
from the previous run.
"""

from unittest.mock import Mock

import pytest

from agent.memory.session_store import SessionStore
from agent.orchestrator import Orchestrator
from agent.tools.base import BaseTool, ToolResult


class FakeReadmeScorer(BaseTool):
    """Tool whose output changes based on input, so we can detect staleness."""

    name = "readme_scorer"
    description = "Fake readme scorer for tests"

    def execute(self, input_data: dict) -> ToolResult:
        return ToolResult(
            success=True,
            data={"readme_content": input_data["readme_content"]},
        )


class FakeSkillExtractor(BaseTool):
    """Tool that only runs when resume_text is present in the profile."""

    name = "skill_extractor"
    description = "Fake skill extractor for tests"

    def execute(self, input_data: dict) -> ToolResult:
        return ToolResult(
            success=True,
            data={"resume_text": input_data["resume_text"]},
        )


@pytest.mark.unit
class TestOrchestratorSessionClearing:
    """Test suite for session state handling across repeated reviews."""

    @pytest.fixture
    def mock_redis(self) -> Mock:
        """Create a mock Redis client backed by an in-memory dict."""
        store: dict[str, str] = {}
        redis = Mock()
        redis.get = Mock(side_effect=lambda key: store.get(key))
        redis.setex = Mock(side_effect=lambda key, ttl, value: store.__setitem__(key, value))
        redis.delete = Mock(side_effect=lambda key: store.pop(key, None))
        return redis

    @pytest.fixture
    def session_store(self, mock_redis: Mock) -> SessionStore:
        """Create a SessionStore backed by the mock Redis client."""
        return SessionStore(mock_redis)

    @pytest.fixture
    def orchestrator(self, session_store: SessionStore) -> Orchestrator:
        """Create an Orchestrator wired with fake tools and a real SessionStore."""
        tools = {
            "readme_scorer": FakeReadmeScorer(),
            "skill_extractor": FakeSkillExtractor(),
        }
        return Orchestrator(tools=tools, session_store=session_store)

    def test_second_review_reflects_updated_profile_data(self, orchestrator: Orchestrator) -> None:
        """After the profile changes, re-running should return the new data, not stale data."""
        profile_id = "profile-123"

        profile_v1 = {"readme_content": "original readme"}
        profile_v2 = {"readme_content": "updated readme"}

        result_v1 = orchestrator.run(profile_id, profile_v1)
        result_v2 = orchestrator.run(profile_id, profile_v2)

        assert result_v1["tool_results"]["readme_scorer"]["readme_content"] == "original readme"
        # This is expected to currently FAIL until issue #43 is fixed:
        # stale session state causes the second run's results to be
        # merged with / overridden by the first run's cached data.
        assert result_v2["tool_results"]["readme_scorer"]["readme_content"] == "updated readme"

    def test_removed_tool_output_does_not_linger_in_session(
        self, orchestrator: Orchestrator, session_store: SessionStore
    ) -> None:
        """If a user removes content (e.g. deletes their resume), the stale
        tool output for that removed input should not persist in the
        session forever.

        Reproduces issue #43: orchestrator.run() merges new results into
        session_state via `session_state.update(results)` but nothing ever
        clears stale keys or calls session_store.delete(), so a tool result
        computed against old profile data can outlive the data it came from.
        """
        profile_id = "profile-456"

        # First review: profile has both a readme and a resume.
        orchestrator.run(
            profile_id,
            {"readme_content": "v1 readme", "resume_text": "v1 resume"},
        )

        # User deletes their resume and re-requests a review.
        orchestrator.run(profile_id, {"readme_content": "v2 readme"})

        session_state = session_store.get(profile_id)

        assert session_state is not None
        # This is expected to currently FAIL: skill_extractor's stale
        # output from the first run is still present even though the
        # resume that produced it no longer exists.
        assert "skill_extractor" not in session_state
