#!/bin/bash
# FarmApp Backend — Run Integration Tests
# Usage: ./scripts/run-integration-tests.sh
#
# Runs integration tests that require a database connection.
# Expects DATABASE_URL environment variable to be set.
# These tests run on PR validation and merge pipelines.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create test results directory
mkdir -p test-results

echo "============================================"
echo " FarmApp Backend — Integration Tests"
echo "============================================"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "⚠️  WARNING: DATABASE_URL is not set."
    echo "   Integration tests will be skipped."
    echo "   Set DATABASE_URL to run against a real database."
    echo ""
    echo "   Example:"
    echo "   export DATABASE_URL='postgresql://user:pass@localhost:5432/farmapp_test'"
    echo ""
    # Create empty results file so pipeline doesn't fail
    echo '<?xml version="1.0" encoding="utf-8"?><testsuites></testsuites>' > test-results/integration-results.xml
    exit 0
fi

echo "Database: $DATABASE_URL"
echo ""

# Run pytest with integration marker
python -m pytest tests/ \
    -m integration \
    --junitxml=test-results/integration-results.xml \
    --cov=. --cov-config=.coveragerc \
    --cov-report=xml:coverage-integration.xml \
    --cov-report=term-missing \
    -v

echo ""
echo "✅ Integration tests completed successfully."
echo "   Results: test-results/integration-results.xml"
echo "   Coverage: coverage-integration.xml"
