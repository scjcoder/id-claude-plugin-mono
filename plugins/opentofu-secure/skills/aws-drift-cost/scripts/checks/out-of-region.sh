#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Region guardrail (detective). Flags ANY resource found outside
#               the home regions (AWS_DRIFT_REGIONS) across all enabled regions,
#               via the Resource Groups Tagging API. Report-only — this is the
#               safe alternative to a hard region lock (the management account
#               can't be SCP-restricted and its permission sets are shared).
# Last updated: 2026-06-23
# Version     : 1.0.0
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/../lib/common.sh"

# Tagging response -> findings, one per resource, tagged with its region.
transform() {
  jq --arg region "$1" '[ .ResourceTagMappingList[]
    | { region: $region, arn: .ResourceARN,
        service: (.ResourceARN | split(":")[2]) } ]'
}

is_home() {
  local region="$1" h
  for h in $REGIONS; do [[ "$region" == "$h" ]] && return 0; done
  return 1
}

if [[ "$MOCK" == "1" ]]; then
  findings="$(aws_json out-of-region resourcegroupstaggingapi get-resources \
    | transform ap-south-1)"
else
  mapfile -t enabled < <(aws_region us-east-1 ec2 describe-regions \
    | jq -r '.Regions[].RegionName')
  tmp="$(mktemp -d)"
  for region in "${enabled[@]}"; do
    is_home "$region" && continue
    (
      out="$(aws_region "$region" resourcegroupstaggingapi get-resources 2>/dev/null \
        | transform "$region")" || out='[]'
      printf '%s' "${out:-[]}" > "$tmp/$region"
    ) &
  done
  wait
  # find (not cat glob) so an empty dir can't trip pipefail.
  findings="$(find "$tmp" -type f -exec cat {} + 2>/dev/null | jq -s 'add // []')"
  rm -rf "$tmp"
fi

emit_check out-of-region "$findings"
