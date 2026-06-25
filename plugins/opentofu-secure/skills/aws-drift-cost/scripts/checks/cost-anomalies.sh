#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Cost-anomaly check — daily Cost Explorer spend per service vs a
#               trailing baseline. Report-only. Emits a check-result object.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/../lib/common.sh"

WINDOW_DAYS="${AWS_DRIFT_COST_WINDOW:-8}"
START="$(days_ago "$WINDOW_DAYS")"
END="$(days_ago 0)"

raw="$(aws_json cost-and-usage ce get-cost-and-usage \
  --time-period "Start=$START,End=$END" \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE)"

result="$(printf '%s' "$raw" \
  | python3 "$HERE/../lib/cost_anomalies.py" --pct "$COST_PCT" --usd "$COST_USD")"

findings="$(printf '%s' "$result" | jq '.findings')"
emit_check cost-anomalies "$findings"
