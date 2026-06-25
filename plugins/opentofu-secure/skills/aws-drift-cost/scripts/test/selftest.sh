#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Offline verification gate for the aws-drift-cost loop. Lints
#               every script, runs the full loop in mock mode against fixtures,
#               and asserts the report JSON + digest match expected counts.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SCRIPTS="$(cd "$HERE/.." && pwd)"
FIXTURES="$HERE/fixtures"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass() { printf '  PASS  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*" >&2; exit 1; }

# --- 1. Syntax + lint -------------------------------------------------------
mapfile -t SH_FILES < <(find "$SKILL_SCRIPTS" -name '*.sh')
for f in "${SH_FILES[@]}"; do
  bash -n "$f" || fail "bash -n: $f"
done
pass "bash -n on ${#SH_FILES[@]} scripts"

if command -v shellcheck >/dev/null 2>&1; then
  # SC1091: sourced libs always exist at runtime but shellcheck can't follow them
  # statically across the batch — exclude it; keep every real check enabled.
  shellcheck -x -e SC1091 "${SH_FILES[@]}" || fail "shellcheck reported issues"
  pass "shellcheck clean"
else
  printf '  SKIP  shellcheck not installed\n'
fi

# --- 2. Run the loop in mock mode -------------------------------------------
report="$TMP/report.json"
digest="$TMP/digest.md"
htmlout="$TMP/report.html"
"$SKILL_SCRIPTS/run-loop.sh" --mock "$FIXTURES" \
  --json "$report" --digest "$digest" --html "$htmlout" >/dev/null

jq empty "$report" || fail "report is not valid JSON"
pass "report JSON is valid"

# --- 3. Assert finding counts -----------------------------------------------
assert_count() {
  local check="$1" want="$2" got
  got="$(jq --arg c "$check" '.checks[] | select(.check==$c) | .count' "$report")"
  [[ "$got" == "$want" ]] || fail "$check: expected $want findings, got $got"
  pass "$check → $got finding(s)"
}
assert_count cost-anomalies 1
assert_count cost-trend 2
assert_count untagged 1
assert_count public-encryption-drift 4
assert_count idle-orphaned 3
assert_count out-of-region 2

total="$(jq '.total_findings' "$report")"
[[ "$total" == "13" ]] || fail "total_findings expected 13, got $total"
pass "total_findings = 13"

# Out-of-region guardrail: findings carry the stray region.
oor_region="$(jq -r '[.checks[]|select(.check=="out-of-region").findings[].region][0]' "$report")"
[[ "$oor_region" == "ap-south-1" ]] || fail "out-of-region missing region, got $oor_region"
pass "out-of-region flags stray-region resources"

# Cost watchlist must catch the excluded Security Hub spend.
hub="$(jq -r '[.checks[] | select(.check=="cost-trend") | .findings[]
  | select(.kind=="excluded") | .service] | join(",")' "$report")"
[[ "$hub" == *"Security Hub"* ]] || fail "watchlist missed Security Hub, got: $hub"
pass "cost watchlist flags excluded service (Security Hub)"

# DNS correlation: 2 buckets DNS-backed (name + target match), 1 S3 review + 1 EBS.
drift_q='.checks[] | select(.check=="public-encryption-drift") | .findings'
dns_backed="$(jq "[ ${drift_q}[] | select(.dns_backed==true) ] | length" "$report")"
[[ "$dns_backed" == "2" ]] || fail "expected 2 DNS-backed buckets, got $dns_backed"
review="$(jq "[ ${drift_q}[] | select(.dns_backed!=true) ] | length" "$report")"
[[ "$review" == "2" ]] || fail "expected 2 review items (no DNS), got $review"
pass "DNS correlation: 2 DNS-backed, 2 review"

oops_backed="$(jq -r "[ ${drift_q}[] | select(.name==\"scj-dev-public-oops\") | .dns_backed ][0]" "$report")"
[[ "$oops_backed" == "false" ]] || fail "scj-dev-public-oops should be a review candidate"
pass "bucket with no DNS record flagged for review"

# Multi-region: findings carry a region; the mock EBS volume is in eu-west-1.
ebs_region="$(jq -r "[ ${drift_q}[] | select(.type==\"ebs-volume\") | .region ][0]" "$report")"
[[ "$ebs_region" == "eu-west-1" ]] || fail "EBS finding missing eu-west-1 region, got $ebs_region"
pass "multi-region: findings tagged with region"

# --- 4. Spot-check transforms -----------------------------------------------
svc="$(jq -r '.checks[] | select(.check=="cost-anomalies") | .findings[0].service' "$report")"
[[ "$svc" == *"Elastic Compute Cloud"* ]] || fail "cost anomaly service wrong: $svc"
pass "cost anomaly identifies EC2 spike"

savings="$(jq '[.checks[] | select(.check=="idle-orphaned") | .findings[].est_monthly_usd] | add' "$report")"
# 3.60 (EIP) + 8.00 (100GB * 0.08) + 32.40 (NAT) = 44.00
[[ "$savings" == "44" || "$savings" == "44.0" ]] || fail "idle savings expected 44, got $savings"
pass "idle savings sum = \$44.00/mo"

# --- 5. Digest renders ------------------------------------------------------
grep -q "AWS drift & cost" "$digest" || fail "digest missing header"
grep -q "Potential idle savings" "$digest" || fail "digest missing savings line"
grep -q "Elastic Compute Cloud" "$digest" || fail "digest missing cost table"
grep -q "Review — no DNS record" "$digest" || fail "digest missing review section"
grep -q "DNS-backed S3" "$digest" || fail "digest missing DNS-backed section"
grep -q "Excluded services" "$digest" || fail "digest missing watchlist section"
grep -q "trailing 3-month baseline" "$digest" || fail "digest missing trend section"
pass "digest renders all sections"

# --- 6. HTML report renders -------------------------------------------------
grep -q "<!doctype html>" "$htmlout" || fail "html missing doctype"
grep -q "AWS drift &amp; cost" "$htmlout" || fail "html missing header"
grep -q "Review — no DNS record" "$htmlout" || fail "html missing review block"
grep -q "scj-dev-public-oops" "$htmlout" || fail "html missing review bucket row"
python3 -c "import html.parser,sys
class P(html.parser.HTMLParser):
    pass
P().feed(open('$htmlout').read())" || fail "html does not parse"
pass "html report renders and parses"

printf '\nALL CHECKS PASSED\n'
