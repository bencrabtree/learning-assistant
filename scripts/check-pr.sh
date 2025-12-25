#!/bin/bash
# Pre-PR Quality Check Script
# Run this before creating a PR to ensure all checks will pass in GitHub Actions

set -e  # Exit on first error

echo "🔍 Running Pre-PR Quality Checks..."
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# 1. Black formatting
echo "📝 Checking code formatting (Black)..."
if black --check --line-length=100 . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Black formatting passed${NC}"
else
    echo -e "${RED}✗ Black formatting failed${NC}"
    echo "  Run: black --line-length=100 ."
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 2. Import sorting
echo "📦 Checking import sorting (isort)..."
if isort --check-only --profile=black --line-length=100 . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Import sorting passed${NC}"
else
    echo -e "${RED}✗ Import sorting failed${NC}"
    echo "  Run: isort --profile=black --line-length=100 ."
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 3. Linting
echo "🔎 Running linter (Ruff)..."
if ruff check src/ tests/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ruff linting passed${NC}"
else
    echo -e "${RED}✗ Ruff linting failed${NC}"
    echo "  Run: ruff check --fix src/ tests/"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 4. Type checking (don't fail on this yet)
echo "🔬 Running type checker (MyPy)..."
if mypy src/ --config-file=pyproject.toml > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MyPy type checking passed${NC}"
else
    echo -e "${YELLOW}⚠ MyPy type checking has warnings (not blocking)${NC}"
fi
echo ""

# 5. Security scan
echo "🔒 Running security scan (Bandit)..."
if bandit -r src/ -c pyproject.toml > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Bandit security scan passed${NC}"
else
    echo -e "${RED}✗ Bandit security scan failed${NC}"
    echo "  Run: bandit -r src/ -c pyproject.toml"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 6. Unit Tests (with coverage requirement)
echo "🧪 Running unit tests with coverage..."
if pytest -v -m "not integration" --cov=src --cov-report=term-missing --cov-fail-under=80 --tb=short > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Unit tests passed with >80% coverage${NC}"
else
    echo -e "${RED}✗ Unit tests failed or coverage <80%${NC}"
    echo "  Run: pytest -v -m \"not integration\" --cov=src --cov-report=term-missing"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 7. Integration Tests (no coverage requirement)
echo "🔗 Running integration tests..."
if pytest -v -m integration --tb=short > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Integration tests failed (not blocking)${NC}"
fi
echo ""

# Summary
echo "===================================="
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to create PR${NC}"
    exit 0
else
    echo -e "${RED}❌ $FAILURES check(s) failed. Fix issues before creating PR${NC}"
    exit 1
fi
