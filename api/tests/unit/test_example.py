"""FarmApp Backend — Example Unit Tests.

These tests are marked with @pytest.mark.unit and do NOT require
any external dependencies (database, network, etc.).
They run on every feature branch push for fast feedback.
"""

import pytest


@pytest.mark.unit
class TestExample:
    """Basic sanity checks for the backend."""

    def test_simple_math(self):
        """Verify basic arithmetic works."""
        assert 1 + 1 == 2
        assert 2 * 3 == 6

    def test_string_operations(self):
        """Verify basic string operations."""
        result = "FarmApp" + " API"
        assert result == "FarmApp API"
        assert "Farm" in result
