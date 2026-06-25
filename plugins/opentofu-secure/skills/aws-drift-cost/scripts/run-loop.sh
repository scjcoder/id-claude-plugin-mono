#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Orchestrate the aws-drift-cost loop — run every check, assemble
#               one report JSON, and (optionally) render a Markdown digest.
#               Report-only: no AWS resource is ever modified.
# Last updated: 2026-06-22
# Version     : 1.0.0
#
# Usage:
#   scripts/run-loop.sh [--json <path>] [--digest <path>] [--mock <dir>]
#
# Env: see lib/common.sh (profile, region, thresholds). AWS_DRIFT_MOCK=1 with
# AWS_DRIFT_MOCK_DIR runs fully offline against fixtures.
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

JSON_OUT=""
DIGEST_OUT=""
HTML_OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)   JSON_OUT="$2"; shift 2 ;;
    --digest) DIGEST_OUT="$2"; shift 2 ;;
    --html)   HTML_OUT="$2"; shift 2 ;;
    --mock)   MOCK=1; MOCK_DIR="$2"; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done

require_deps
preflight_credentials || exit $?

CHECKS=(cost-anomalies cost-trend untagged public-encryption-drift idle-orphaned out-of-region)
results=()
for check in "${CHECKS[@]}"; do
  log "running check: $check"
  if out="$(AWS_DRIFT_MOCK="$MOCK" AWS_DRIFT_MOCK_DIR="$MOCK_DIR" \
      bash "$HERE/checks/$check.sh" 2>/dev/null)"; then
    results+=("$out")
  else
    # One check failing must not sink the whole report — record it and continue.
    warn "check '$check' failed; continuing"
    results+=("$(jq -n --arg c "$check" --arg a "$ACCOUNT_ID" \
      '{check:$c, account:$a, region:"", count:0, findings:[], error:"check failed"}')")
  fi
done

report="$(jq -n \
  --arg generated_at "$(now_iso)" \
  --arg account "$ACCOUNT_ID" \
  --arg profile "$PROFILE" \
  --arg region "$REGION" \
  --argjson checks "$(printf '%s\n' "${results[@]}" | jq -s '.')" \
  '{generated_at:$generated_at, account:$account, profile:$profile,
    region:$region,
    total_findings: ([$checks[].count] | add),
    checks:$checks}')"

if [[ -n "$JSON_OUT" ]]; then
  mkdir -p "$(dirname "$JSON_OUT")"
  printf '%s\n' "$report" > "$JSON_OUT"
  log "wrote report JSON: $JSON_OUT"
fi

if [[ -n "$DIGEST_OUT" ]]; then
  mkdir -p "$(dirname "$DIGEST_OUT")"
  printf '%s' "$report" | python3 "$HERE/lib/render_digest.py" > "$DIGEST_OUT"
  log "wrote digest: $DIGEST_OUT"
fi

if [[ -n "$HTML_OUT" ]]; then
  mkdir -p "$(dirname "$HTML_OUT")"
  printf '%s' "$report" | python3 "$HERE/lib/render_html.py" > "$HTML_OUT"
  log "wrote html: $HTML_OUT"
fi

# Report JSON to stdout for callers/agents that pipe it onward.
printf '%s\n' "$report"
