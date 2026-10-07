#!/bin/bash
# FarmApp Frontend — Run Playwright E2E Tests
# Usage: ./scripts/run-e2e-tests.sh
#
# Runs Playwright end-to-end tests against a deployed environment.
# Expects BASE_URL environment variable to be set (default: http://localhost).
# These tests run on staging/production deployments.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create test results directory
mkdir -p test-results

echo "============================================"
echo " FarmApp Frontend — Playwright E2E Tests"
echo "============================================"

BASE_URL="${BASE_URL:-http://localhost}"

echo "Target URL: $BASE_URL"
echo ""

# Install Playwright browsers if not already installed
npx playwright install chromium --with-deps 2>/dev/null || true

# Run Playwright tests
npx playwright test \
    --config=playwright.config.ts \
    --reporter=list,junit \
    --reporter-junit-output=test-results/e2e-results.xml

echo ""
echo "✅ E2E tests completed successfully."
echo "   Results: test-results/e2e-results.xml"
