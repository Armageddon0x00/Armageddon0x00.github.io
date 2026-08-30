#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPOSITORY_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
CONFIG_PATH="${SCRIPT_DIR}/site-config.json"
CHECKS_SCRIPT="${SCRIPT_DIR}/site_checks.py"
BROWSER_SCRIPT="${SCRIPT_DIR}/browser_tools.py"
DEPLOY_SCRIPT="${SCRIPT_DIR}/verify-deployment.sh"

PREVIEW_HOST=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["preview_host"])' "$CONFIG_PATH")
PREVIEW_PORT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["preview_port"])' "$CONFIG_PATH")
PREVIEW_URL="http://${PREVIEW_HOST}:${PREVIEW_PORT}"
PREVIEW_PID_FILE="/tmp/catakan-site-preview-${PREVIEW_PORT}.pid"
PREVIEW_LOG_FILE="/tmp/catakan-site-preview-${PREVIEW_PORT}.log"

usage() {
  cat <<'EOF'
Usage: .github/scripts/site.sh COMMAND [options]

Mandatory operator toolkit for catakan.net.

Commands:
  preview [start|foreground|status|stop]
                               Start, hold, inspect, or stop the local preview
  check                        Run the complete static pre-commit gate
  content                      Validate durable content invariants
  assets                       Validate and inventory local assets
  audit                        Audit layout, snapping, errors, and reduced motion
  capture [--output DIR]       Capture every snap section at all viewports
  review [--output DIR]        Run check, audit, and capture in sequence
  deploy [VERIFY OPTIONS]      Run exact-commit post-push verification
  help                         Show this help

Generated logs, reports, profiles, and screenshots are written only under /tmp.
EOF
}

fail() {
  printf 'FAIL  %s\n' "$*" >&2
  exit 1
}

pass() {
  printf 'PASS  %s\n' "$*"
}

require_commands() {
  local command_name
  for command_name in "$@"; do
    command -v "$command_name" >/dev/null || fail "required command not found: ${command_name}"
  done
}

preview_matches_repository() {
  local root_html ataturk_html
  root_html=$(curl -LfsS --max-time 3 "${PREVIEW_URL}/" 2>/dev/null) || return 1
  ataturk_html=$(curl -LfsS --max-time 3 "${PREVIEW_URL}/ataturk/" 2>/dev/null) || return 1
  grep -Fq '<title>Catakan — Somewhere in the wire</title>' <<<"$root_html" || return 1
  grep -Fq '<title>Atatürk Köşesi — Catakan</title>' <<<"$ataturk_html" || return 1
}

preview_status() {
  require_commands curl
  if preview_matches_repository; then
    pass "preview is serving this repository"
    printf '      main      %s/\n' "$PREVIEW_URL"
    printf '      ataturk  %s/ataturk/\n' "$PREVIEW_URL"
    if [[ -f "$PREVIEW_PID_FILE" ]]; then
      printf '      pid       %s\n' "$(<"$PREVIEW_PID_FILE")"
    else
      printf '      process   existing/unmanaged\n'
    fi
    return 0
  fi
  printf 'STOP  no matching preview at %s\n' "$PREVIEW_URL"
  return 1
}

preview_start() {
  require_commands curl python3
  if preview_matches_repository; then
    preview_status
    return 0
  fi

  if curl -LsS --max-time 2 -o /dev/null "${PREVIEW_URL}/" 2>/dev/null; then
    fail "port ${PREVIEW_PORT} is occupied by a different site or process"
  fi

  if [[ -f "$PREVIEW_PID_FILE" ]]; then
    local stale_pid stale_cwd stale_command
    stale_pid=$(<"$PREVIEW_PID_FILE")
    if [[ "$stale_pid" =~ ^[0-9]+$ ]] && kill -0 "$stale_pid" 2>/dev/null; then
      stale_cwd=$(readlink -f "/proc/${stale_pid}/cwd" 2>/dev/null || true)
      stale_command=$(tr '\0' ' ' <"/proc/${stale_pid}/cmdline" 2>/dev/null || true)
      if [[ "$stale_cwd" == "$REPOSITORY_ROOT" && "$stale_command" == *"http.server ${PREVIEW_PORT}"* ]]; then
        fail "managed preview process ${stale_pid} is running, but the site is unavailable; inspect ${PREVIEW_LOG_FILE}"
      fi
    fi
    rm -f -- "$PREVIEW_PID_FILE"
  fi

  cd "$REPOSITORY_ROOT"
  nohup python3 -m http.server "$PREVIEW_PORT" --bind "$PREVIEW_HOST" \
    </dev/null >"$PREVIEW_LOG_FILE" 2>&1 &
  local preview_pid=$!
  printf '%s\n' "$preview_pid" >"$PREVIEW_PID_FILE"

  local attempt
  for attempt in {1..40}; do
    if preview_matches_repository; then
      pass "started repository preview"
      preview_status
      printf '      log       %s\n' "$PREVIEW_LOG_FILE"
      return 0
    fi
    if ! kill -0 "$preview_pid" 2>/dev/null; then
      rm -f -- "$PREVIEW_PID_FILE"
      fail "preview process exited during startup; inspect ${PREVIEW_LOG_FILE}"
    fi
    sleep 0.25
  done

  rm -f -- "$PREVIEW_PID_FILE"
  fail "preview did not become ready; inspect ${PREVIEW_LOG_FILE}"
}

preview_foreground() {
  require_commands curl python3
  if preview_matches_repository; then
    fail "a matching preview is already running at ${PREVIEW_URL}"
  fi
  if curl -LsS --max-time 2 -o /dev/null "${PREVIEW_URL}/" 2>/dev/null; then
    fail "port ${PREVIEW_PORT} is occupied by a different site or process"
  fi
  printf 'HOLD  repository preview in foreground\n'
  printf '      main      %s/\n' "$PREVIEW_URL"
  printf '      ataturk  %s/ataturk/\n' "$PREVIEW_URL"
  printf '      stop      Ctrl-C\n'
  cd "$REPOSITORY_ROOT"
  exec python3 -m http.server "$PREVIEW_PORT" --bind "$PREVIEW_HOST"
}

preview_stop() {
  if [[ ! -f "$PREVIEW_PID_FILE" ]]; then
    if preview_matches_repository; then
      fail "the preview is running but was not started by this toolkit; leaving it untouched"
    fi
    pass "preview is already stopped"
    return 0
  fi

  local pid process_cwd process_command
  pid=$(<"$PREVIEW_PID_FILE")
  [[ "$pid" =~ ^[0-9]+$ ]] || fail "invalid preview PID file: ${PREVIEW_PID_FILE}"
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f -- "$PREVIEW_PID_FILE"
    pass "removed stale preview PID file"
    return 0
  fi

  process_cwd=$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)
  process_command=$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)
  [[ "$process_cwd" == "$REPOSITORY_ROOT" ]] || fail "refusing to stop PID ${pid}: working directory does not match repository"
  [[ "$process_command" == *"http.server ${PREVIEW_PORT}"* ]] || fail "refusing to stop PID ${pid}: command is not the managed preview"

  kill "$pid"
  local attempt
  for attempt in {1..20}; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  rm -f -- "$PREVIEW_PID_FILE"
  pass "stopped preview PID ${pid}"
}

check_endpoints() {
  local endpoint status
  while IFS= read -r endpoint; do
    status=$(curl -LsS --max-time 10 -o /dev/null -w '%{http_code}' "${PREVIEW_URL}${endpoint}" || true)
    [[ "$status" == "200" ]] || fail "local endpoint ${endpoint} returned HTTP ${status:-000}"
    pass "HTTP 200 ${endpoint}"
  done < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["required_endpoints"]))' "$CONFIG_PATH")
}

check_changed_public_files() {
  local changed_path status
  while IFS= read -r changed_path; do
    [[ -n "$changed_path" ]] || continue
    case "$changed_path" in
      .github/*|.gitignore|.nojekyll|AGENTS.md|CNAME)
        continue
        ;;
    esac
    [[ -f "${REPOSITORY_ROOT}/${changed_path}" ]] || continue
    status=$(curl -LsS --max-time 10 -o /dev/null -w '%{http_code}' "${PREVIEW_URL}/${changed_path}" || true)
    [[ "$status" == "200" ]] || fail "changed public file /${changed_path} returned HTTP ${status:-000}"
    pass "changed public file is served: /${changed_path}"
  done < <(
    cd "$REPOSITORY_ROOT"
    {
      git diff --name-only --diff-filter=ACMRT HEAD
      git ls-files --others --exclude-standard
    } | sort -u
  )
}

run_content() {
  require_commands python3
  python3 "$CHECKS_SCRIPT" content
}

run_assets() {
  require_commands python3
  python3 "$CHECKS_SCRIPT" assets
}

run_check() {
  require_commands curl git python3 xmllint
  cd "$REPOSITORY_ROOT"
  printf 'STATIC PRE-COMMIT GATE\n'
  git diff --check
  pass "git diff --check"
  xmllint --html --noout index.html
  pass "index.html parses with xmllint"
  xmllint --html --noout ataturk/index.html
  pass "ataturk/index.html parses with xmllint"
  run_content
  run_assets
  preview_start
  check_endpoints
  check_changed_public_files
  printf 'PASSED static pre-commit gate\n'
}

run_audit() {
  require_commands python3
  preview_start
  python3 "$BROWSER_SCRIPT" audit --base-url "$PREVIEW_URL"
}

run_capture() {
  require_commands python3
  preview_start
  python3 "$BROWSER_SCRIPT" capture --base-url "$PREVIEW_URL" "$@"
}

run_review() {
  run_check
  run_audit
  run_capture "$@"
}

COMMAND=${1:-help}
if (($#)); then
  shift
fi

case "$COMMAND" in
  preview)
    PREVIEW_COMMAND=${1:-start}
    case "$PREVIEW_COMMAND" in
      start) preview_start ;;
      foreground) preview_foreground ;;
      status) preview_status ;;
      stop) preview_stop ;;
      *) fail "unknown preview command: ${PREVIEW_COMMAND}" ;;
    esac
    ;;
  check)
    (($# == 0)) || fail "check does not accept options"
    run_check
    ;;
  content)
    (($# == 0)) || fail "content does not accept options"
    run_content
    ;;
  assets)
    (($# == 0)) || fail "assets does not accept options"
    run_assets
    ;;
  audit)
    (($# == 0)) || fail "audit does not accept options"
    run_audit
    ;;
  capture)
    run_capture "$@"
    ;;
  review)
    run_review "$@"
    ;;
  deploy)
    require_commands curl git jq
    exec "$DEPLOY_SCRIPT" "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    fail "unknown command: ${COMMAND}; run '$0 help'"
    ;;
esac
