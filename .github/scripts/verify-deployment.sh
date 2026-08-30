#!/usr/bin/env bash

set -euo pipefail

REPOSITORY="Armageddon0x00/Armageddon0x00.github.io"
BRANCH="main"
SITE_URL="https://catakan.net"
EXPECTED_SHA="HEAD"
MARKER=""
ABSENT_MARKER=""
TIMEOUT_SECONDS=600
POLL_INTERVAL=5

usage() {
  cat <<'EOF'
Usage: .github/scripts/verify-deployment.sh [options]

Wait for and verify the GitHub Pages deployment for a commit.

Options:
  --sha SHA          Commit to verify (default: HEAD)
  --marker TEXT      Text that must appear in the deployed root HTML
  --absent TEXT      Text that must not appear in the deployed root HTML
  --timeout SECONDS  Maximum workflow wait (default: 600)
  --interval SECONDS Poll interval (default: 5)
  -h, --help         Show this help

GITHUB_TOKEN may be set to increase the GitHub API rate limit.
EOF
}

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

pass() {
  printf 'PASS  %s\n' "$*"
}

while (($#)); do
  case "$1" in
    --sha)
      (($# >= 2)) || fail "--sha requires a value"
      EXPECTED_SHA="$2"
      shift 2
      ;;
    --marker)
      (($# >= 2)) || fail "--marker requires a value"
      MARKER="$2"
      shift 2
      ;;
    --absent)
      (($# >= 2)) || fail "--absent requires a value"
      ABSENT_MARKER="$2"
      shift 2
      ;;
    --timeout)
      (($# >= 2)) || fail "--timeout requires a value"
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --interval)
      (($# >= 2)) || fail "--interval requires a value"
      POLL_INTERVAL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1"
      ;;
  esac
done

for command_name in curl git jq; do
  command -v "$command_name" >/dev/null || fail "required command not found: $command_name"
done

[[ "$TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "timeout must be a positive integer"
[[ "$POLL_INTERVAL" =~ ^[1-9][0-9]*$ ]] || fail "interval must be a positive integer"

REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
cd "$REPOSITORY_ROOT"

EXPECTED_SHA=$(git rev-parse "${EXPECTED_SHA}^{commit}")

printf 'VERIFY catakan.net deployment\n'
printf '      commit %s\n' "$EXPECTED_SHA"

git fetch origin "$BRANCH" --quiet

LOCAL_SHA=$(git rev-parse HEAD)
TRACKING_SHA=$(git rev-parse "origin/${BRANCH}")
PUBLIC_SHA=$(git ls-remote origin "refs/heads/${BRANCH}" | cut -f1)

[[ "$LOCAL_SHA" == "$EXPECTED_SHA" ]] || fail "local HEAD is ${LOCAL_SHA}, expected ${EXPECTED_SHA}"
[[ "$TRACKING_SHA" == "$EXPECTED_SHA" ]] || fail "origin/${BRANCH} is ${TRACKING_SHA}, expected ${EXPECTED_SHA}"
[[ "$PUBLIC_SHA" == "$EXPECTED_SHA" ]] || fail "public ${BRANCH} is ${PUBLIC_SHA}, expected ${EXPECTED_SHA}"
pass "local, tracking, and public branch SHAs match"

CURL_HEADERS=(-H "Accept: application/vnd.github+json")
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  CURL_HEADERS+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

ACTIONS_API="https://api.github.com/repos/${REPOSITORY}/actions/runs?head_sha=${EXPECTED_SHA}&branch=${BRANCH}&per_page=10"
WAIT_STARTED=$(date +%s)
RUN_URL=""

while true; do
  RUN_DATA=$(curl -LfsS "${CURL_HEADERS[@]}" "$ACTIONS_API")
  RUN_ID=$(jq -r '.workflow_runs[0].id // empty' <<<"$RUN_DATA")
  RUN_STATUS=$(jq -r '.workflow_runs[0].status // "waiting"' <<<"$RUN_DATA")
  RUN_CONCLUSION=$(jq -r '.workflow_runs[0].conclusion // "pending"' <<<"$RUN_DATA")
  RUN_URL=$(jq -r '.workflow_runs[0].html_url // empty' <<<"$RUN_DATA")

  if [[ -n "$RUN_ID" && "$RUN_STATUS" == "completed" ]]; then
    [[ "$RUN_CONCLUSION" == "success" ]] || fail "Pages run ${RUN_ID} completed with ${RUN_CONCLUSION}: ${RUN_URL}"
    break
  fi

  ELAPSED_SECONDS=$(( $(date +%s) - WAIT_STARTED ))
  (( ELAPSED_SECONDS < TIMEOUT_SECONDS )) || fail "Pages run did not succeed within ${TIMEOUT_SECONDS}s"

  printf 'WAIT  Pages workflow: %s / %s (%ss elapsed)\n' "$RUN_STATUS" "$RUN_CONCLUSION" "$ELAPSED_SECONDS"
  sleep "$POLL_INTERVAL"
done

pass "Pages workflow completed successfully: ${RUN_URL}"

LIVE_STARTED=$(date +%s)

while true; do
  LIVE_REASON=""

  for endpoint in "/" "/ataturk/" "/.well-known/security.txt"; do
    HTTP_STATUS=$(curl -LsS -o /dev/null -w '%{http_code}' "${SITE_URL}${endpoint}" || true)
    if [[ "$HTTP_STATUS" != "200" ]]; then
      LIVE_REASON="${endpoint} returned HTTP ${HTTP_STATUS:-000}"
      break
    fi
  done

  if [[ -z "$LIVE_REASON" ]]; then
    ROOT_HTML=$(curl -LfsS "${SITE_URL}/" || true)

    if [[ -n "$MARKER" ]] && ! grep -Fq -- "$MARKER" <<<"$ROOT_HTML"; then
      LIVE_REASON="root HTML does not yet contain the expected marker"
    elif [[ -n "$ABSENT_MARKER" ]] && grep -Fq -- "$ABSENT_MARKER" <<<"$ROOT_HTML"; then
      LIVE_REASON="root HTML still contains the removed marker"
    fi
  fi

  if [[ -z "$LIVE_REASON" ]]; then
    break
  fi

  ELAPSED_SECONDS=$(( $(date +%s) - LIVE_STARTED ))
  (( ELAPSED_SECONDS < TIMEOUT_SECONDS )) || fail "live deployment did not become ready within ${TIMEOUT_SECONDS}s: ${LIVE_REASON}"

  printf 'WAIT  Live deployment: %s (%ss elapsed)\n' "$LIVE_REASON" "$ELAPSED_SECONDS"
  sleep "$POLL_INTERVAL"
done

pass "HTTP 200 /, /ataturk/, and /.well-known/security.txt"
[[ -z "$MARKER" ]] || pass "deployed root HTML contains expected marker"
[[ -z "$ABSENT_MARKER" ]] || pass "removed marker is absent from deployed root HTML"

TOOLING_STATUS=$(curl -LsS -o /dev/null -w '%{http_code}' "${SITE_URL}/.github/scripts/verify-deployment.sh" || true)
[[ "$TOOLING_STATUS" == "404" ]] || fail "repository tooling is unexpectedly served with HTTP ${TOOLING_STATUS:-000}"
pass "repository tooling is not served by catakan.net"

[[ -z "$(git status --porcelain)" ]] || fail "working tree is not clean"
pass "working tree is clean"

printf '\nDEPLOYED\n'
printf '  commit  %s\n' "$EXPECTED_SHA"
printf '  action  %s\n' "$RUN_URL"
printf '  site    %s/\n' "$SITE_URL"
