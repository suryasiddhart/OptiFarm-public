#!/bin/bash
# FarmApp Frontend — Run Unit Tests
# Usage: ./scripts/run-unit-tests.sh
#
# Runs Vitest unit tests for the frontend.
# These tests are fast and suitable for feature branch validation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create test results directory
mkdir -p test-results

echo "============================================"
echo " FarmApp Frontend — Unit Tests"
echo "============================================"

# Run Vitest (pinned in devDependencies) with JUnit + console reporters.
# Coverage: lcov (SonarQube) and cobertura (Azure DevOps Code Coverage tab).
npx vitest run \
    --reporter=default \
    --reporter=junit \
    --outputFile.junit=test-results/unit-results.xml \
    --coverage.enabled=true \
    --coverage.reporter=lcov \
    --coverage.reporter=cobertura \
    --coverage.reportsDirectory=coverage

echo ""
echo "✅ Frontend unit tests completed successfully."
echo "   Results: test-results/unit-results.xml"
echo "   Coverage: coverage/"
