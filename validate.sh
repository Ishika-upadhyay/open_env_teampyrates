#!/usr/bin/env bash
set -uo pipefail

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  printf "Usage: %s <ping_url> [repo_dir]\n" "$0"
  exit 1
fi

PING_URL="${PING_URL%/}"
PASS=0

log()  { printf "[%s] %b\n" "$(date -u +%H:%M:%S)" "$*"; }
pass() { log "\033[0;32mPASSED\033[0m -- $1"; PASS=$((PASS + 1)); }
fail() { log "\033[0;31mFAILED\033[0m -- $1"; exit 1; }

log "Step 1/3: Pinging HF Space ($PING_URL/reset) ..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$PING_URL/reset" --max-time 30 || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
  pass "HF Space is live and responds to /reset"
else
  fail "HF Space /reset returned HTTP $HTTP_CODE. Make sure your Space is running."
fi

log "Step 2/3: Running docker build ..."
if docker build "$REPO_DIR" > /dev/null 2>&1; then
  pass "Docker build succeeded"
else
  fail "Docker build failed"
fi

log "Step 3/3: Running openenv validate ..."
if cd "$REPO_DIR" && openenv validate > /dev/null 2>&1; then
  pass "openenv validate passed"
else
  fail "openenv validate failed"
fi

printf "\n\033[0;32m\033[1m  All 3/3 checks passed!\033[0m\n"
printf "\033[0;32m\033[1m  Your submission is ready to submit.\033[0m\n\n"