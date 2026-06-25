#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Long-horizon cost check — per-service deviation vs a trailing
#               3-month baseline, plus an excluded-services watchlist (any spend
#               on Security Hub / GuardDuty / WAF / Inspector / Shield Advanced).
#               Report-only. Cost Explorer is global (no region loop).
# Last updated: 2026-06-23
# Version     : 1.0.0
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/../lib/common.sh"

TREND_PCT="${AWS_DRIFT_TREND_PCT:-40}"
TREND_USD="${AWS_DRIFT_TREND_USD:-10}"
WATCH="${AWS_DRIFT_COST_WATCH:-security hub,guardduty,waf,inspector,shield advanced,macie,detective,sagemaker,redshift,opensearch,elasticsearch,kafka,elasticache,emr,kendra,neptune,documentdb,appstream,workspaces,managed grafana,managed service for prometheus,comprehend,rekognition,transcribe}"
MONTHS="${AWS_DRIFT_TREND_MONTHS:-4}"   # 3 baseline months + current partial

START="$(python3 -c "import datetime as d,sys
t=d.date.today().replace(day=1); n=int(sys.argv[1])
m=t.month-n; y=t.year+(m-1)//12
print(d.date(y,(m-1)%12+1,1).isoformat())" "$MONTHS")"
END="$(days_ago 0)"

raw="$(aws_json cost-monthly ce get-cost-and-usage \
  --time-period "Start=$START,End=$END" \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE)"

findings="$(printf '%s' "$raw" \
  | python3 "$HERE/../lib/cost_trend.py" \
      --pct "$TREND_PCT" --usd "$TREND_USD" --watch "$WATCH" \
  | jq '.findings')"

emit_check cost-trend "$findings"
