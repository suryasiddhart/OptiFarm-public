#!/bin/bash
# FarmApp Backend — Run Unit Tests
# Usage: ./scripts/run-unit-tests.sh
#
# Runs only unit tests (no external dependencies required).
# These tests are fast and suitable for feature branch validation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create test results directory
mkdir -p test-results

echo "============================================"
echo " FarmApp Backend — Unit Tests"
echo "============================================"

# Run pytest with unit marker only
python -m pytest tests/ \
    -m unit \
    --junitxml=test-results/unit-results.xml \
    --cov=. --cov-config=.coveragerc \
    --cov-report=xml:coverage.xml \
    --cov-report=term-missing \
    -v

echo ""
echo "✅ Unit tests completed successfully."
echo "   Results: test-results/unit-results.xml"
echo "   Coverage: coverage.xml"
