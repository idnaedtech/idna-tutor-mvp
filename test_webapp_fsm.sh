#!/bin/bash
# Test FSM flow through webapp API
# Usage: ./test_webapp_fsm.sh [BASE_URL]

BASE_URL="${1:-https://idna-tutor-mvp-production.up.railway.app}"
STUDENT_ID="test-$(date +%s)"

echo "========================================"
echo "FSM WEBAPP API TEST"
echo "Base URL: $BASE_URL"
echo "Student ID: $STUDENT_ID"
echo "========================================"

# Helper function
call_api() {
    local endpoint=$1
    local data=$2
    echo ""
    echo ">>> $endpoint"
    echo "Request: $data"
    echo "---"
    curl -s -X POST "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data" | python3 -m json.tool 2>/dev/null || curl -s -X POST "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data"
    echo ""
}

# 1. Health check
echo ""
echo "[0] Health Check"
curl -s "$BASE_URL/healthz" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/healthz"

# 2. Start Session -> EXPLAIN
echo ""
echo "[1] StartSession -> Expect EXPLAIN state (1)"
RESP=$(curl -s -X POST "$BASE_URL/start_session" \
    -H "Content-Type: application/json" \
    -d "{\"student_id\": \"$STUDENT_ID\", \"topic_id\": \"addition\"}")
echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"

SESSION_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
echo ""
echo "Session ID: $SESSION_ID"

if [ -z "$SESSION_ID" ]; then
    echo "ERROR: Failed to get session_id"
    exit 1
fi

# 3. Send "ready" -> QUIZ
echo ""
echo "[2] Turn: 'ready' -> Expect QUIZ state (2)"
call_api "/turn" "{\"student_id\": \"$STUDENT_ID\", \"session_id\": \"$SESSION_ID\", \"user_text\": \"ready\"}"

# 4. Send wrong answer -> HINT1
echo ""
echo "[3] Turn: '999' (wrong) -> Expect HINT state (4), intent=hint1"
call_api "/turn" "{\"student_id\": \"$STUDENT_ID\", \"session_id\": \"$SESSION_ID\", \"user_text\": \"999\"}"

# 5. Send wrong answer again -> HINT2
echo ""
echo "[4] Turn: '888' (wrong) -> Expect HINT state (4), intent=hint2"
call_api "/turn" "{\"student_id\": \"$STUDENT_ID\", \"session_id\": \"$SESSION_ID\", \"user_text\": \"888\"}"

# 6. Send wrong answer third time -> REVEAL
echo ""
echo "[5] Turn: '777' (wrong) -> Expect REVEAL state (5), intent=reveal"
call_api "/turn" "{\"student_id\": \"$STUDENT_ID\", \"session_id\": \"$SESSION_ID\", \"user_text\": \"777\"}"

# 7. Try some correct answers
echo ""
echo "[6] Trying correct answers for remaining questions..."
for guess in 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    RESP=$(curl -s -X POST "$BASE_URL/turn" \
        -H "Content-Type: application/json" \
        -d "{\"student_id\": \"$STUDENT_ID\", \"session_id\": \"$SESSION_ID\", \"user_text\": \"$guess\"}")

    INTENT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('intent',''))" 2>/dev/null)
    STATE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('next_state',''))" 2>/dev/null)

    if [ "$INTENT" = "correct" ] || [ "$INTENT" = "complete" ]; then
        echo "  Guess $guess: $INTENT (state=$STATE)"
        if [ "$INTENT" = "complete" ]; then
            echo ""
            echo "SESSION COMPLETE!"
            echo "$RESP" | python3 -m json.tool 2>/dev/null
            break
        fi
    fi
done

echo ""
echo "========================================"
echo "TEST COMPLETE"
echo "========================================"
