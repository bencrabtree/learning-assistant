#!/bin/bash
#
# Comprehensive CI/CD Validation Script
# Runs ALL checks that GitHub Actions will run
# Usage: ./scripts/validate-ci.sh

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILURES=0

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   CI/CD Validation Script${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# ===========================
# 1. Black Formatting Check
# ===========================
echo -e "${BLUE}[1/7]${NC} Checking code formatting with Black..."
if black --check --line-length=100 . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Black formatting check passed${NC}"
else
    echo -e "${RED}✗ Black formatting check FAILED${NC}"
    echo -e "${YELLOW}  Run: black --line-length=100 .${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ===========================
# 2. Import Sorting Check
# ===========================
echo -e "${BLUE}[2/7]${NC} Checking import sorting with isort..."
if isort --check-only --profile=black --line-length=100 . > /dev/null 2>&1; then
    echo -e "${GREEN}✓ isort check passed${NC}"
else
    echo -e "${RED}✗ isort check FAILED${NC}"
    echo -e "${YELLOW}  Run: isort --profile=black --line-length=100 .${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ===========================
# 3. Ruff Linting
# ===========================
echo -e "${BLUE}[3/7]${NC} Linting with Ruff..."
if ruff check src/ tests/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ruff linting passed${NC}"
else
    echo -e "${RED}✗ Ruff linting FAILED${NC}"
    echo -e "${YELLOW}  Run: ruff check src/ tests/${NC}"
    echo -e "${YELLOW}  Auto-fix: ruff check --fix src/ tests/${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ===========================
# 4. MyPy Type Checking
# ===========================
echo -e "${BLUE}[4/7]${NC} Type checking with MyPy..."
if mypy src/ --config-file=pyproject.toml > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MyPy type checking passed${NC}"
else
    echo -e "${YELLOW}⚠ MyPy type checking has warnings (non-blocking)${NC}"
fi
echo ""

# ===========================
# 5. Security Scan with Bandit
# ===========================
echo -e "${BLUE}[5/7]${NC} Running security scan with Bandit..."
if bandit -r src/ -c pyproject.toml > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Bandit security scan passed${NC}"
else
    echo -e "${RED}✗ Bandit security scan FAILED${NC}"
    echo -e "${YELLOW}  Run: bandit -r src/ -c pyproject.toml${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ===========================
# 6. Unit Tests with Coverage
# ===========================
echo -e "${BLUE}[6/7]${NC} Running unit tests with coverage..."
if pytest -v \
    -m "not integration" \
    --cov=src \
    --cov-report=term-missing \
    --cov-fail-under=80 \
    --tb=short > /tmp/pytest-unit.log 2>&1; then
    echo -e "${GREEN}✓ Unit tests passed with >80% coverage${NC}"
    # Show coverage summary
    grep "TOTAL" /tmp/pytest-unit.log | head -1 || true
else
    echo -e "${RED}✗ Unit tests FAILED or coverage <80%${NC}"
    echo -e "${YELLOW}  Run: pytest -v -m \"not integration\" --cov=src --cov-report=term-missing${NC}"
    echo -e "${YELLOW}  See /tmp/pytest-unit.log for details${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# ===========================
# 7. Integration Tests
# ===========================
echo -e "${BLUE}[7/7]${NC} Running integration tests..."
if pytest -v -m integration --tb=short > /tmp/pytest-integration.log 2>&1; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Integration tests failed (non-blocking)${NC}"
    echo -e "${YELLOW}  Run: pytest -v -m integration${NC}"
    echo -e "${YELLOW}  See /tmp/pytest-integration.log for details${NC}"
fi
echo ""

# ===========================
# Summary
# ===========================
echo "===================================="
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All CI/CD checks passed! Safe to push${NC}"
    echo ""
    echo "Next steps:"
    echo "  git push -u origin <branch-name>"
    exit 0
else
    echo -e "${RED}❌ $FAILURES check(s) failed${NC}"
    echo ""
    echo "Fix issues above before pushing to avoid failed CI/CD runs"
    exit 1
fi
