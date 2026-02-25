#!/bin/bash
# IDNA EdTech — Pre-check script
# Run before committing any code changes to the IDNA codebase.
# Usage: bash scripts/pre-check.sh [--quick]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "=== IDNA Pre-Check ==="

# 1. Fatal: app/models/ directory must not exist
if [ -d "app/models" ]; then
    echo -e "${RED}FATAL: app/models/ directory exists — shadows app/models.py${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 2. Fatal: SKILL.md references
if [ -f "README.md" ] && grep -q "SKILL.md" "README.md" 2>/dev/null; then
    echo -e "${YELLOW}WARN: README.md references SKILL.md — keep these separate${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 3. Check TTS voice hasn't been changed (check config.py, not tts.py)
if ! grep -q 'TTS_SPEAKER.*simran' app/config.py 2>/dev/null; then
    echo -e "${RED}FATAL: TTS_SPEAKER not set to 'simran' in config.py — revert immediately${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 4. Check for empty TTS calls (P1 bug #4)
if grep -rn 'tts.*""' app/voice/tts.py 2>/dev/null > /dev/null 2>&1; then
    echo -e "${YELLOW}WARN: Possible empty string TTS call detected${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Quick mode: skip tests
if [ "$1" = "--quick" ]; then
    echo ""
    echo "=== Quick Mode (skipping tests) ==="
    if [ $ERRORS -gt 0 ]; then
        echo -e "${RED}BLOCKED: $ERRORS error(s) found${NC}"
        exit 2
    fi
    echo -e "${GREEN}Quick check passed ($WARNINGS warning(s))${NC}"
    exit 0
fi

# 5. Run verify.py
echo ""
echo "--- Running verify.py ---"
if python verify.py 2>/dev/null; then
    echo -e "${GREEN}verify.py: PASSED${NC}"
else
    echo -e "${RED}FATAL: verify.py failed${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 6. Run tests
echo ""
echo "--- Running tests ---"
if python -m pytest tests/ -x -q 2>/dev/null; then
    echo -e "${GREEN}Tests: PASSED${NC}"
else
    echo -e "${RED}FATAL: Tests failing${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "=== Summary ==="
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}BLOCKED: $ERRORS error(s), $WARNINGS warning(s)${NC}"
    exit 2
else
    echo -e "${GREEN}PASSED: 0 errors, $WARNINGS warning(s)${NC}"
    exit 0
fi
