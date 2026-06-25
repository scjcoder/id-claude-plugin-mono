#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Untagged-resource check — flag resources missing any mandatory
#               tag (Project/Environment/Owner/ManagedBy) via the Resource
#               Groups Tagging API, across every configured region. Report-only.
#               Honors an allowlist (UNTAGGED_EXCLUDE) for resources that are
#               structurally un-taggable, so the count floors at zero.
# Last updated: 2026-06-24
# Version     : 1.2.0
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/../lib/common.sh"

# ---------------------------------------------------------------------------
# Allowlist — ARNs that are STRUCTURALLY un-taggable and must NOT be counted as
# drift (otherwise the report can never reach zero). Extended-regex, matched on
# the full ARN. Override or extend at runtime via the UNTAGGED_EXCLUDE env var.
#
#   :stack/amplify-     Amplify-managed CloudFormation stacks. Tags can't be set
#                       via the tagging API, and the stacks are regenerated with
#                       a fresh random suffix on every Amplify deploy.
#   arn:aws:payments::  AWS-managed billing payment-instruments — not taggable.
#
# Verified 2026-06-24 against account <SCJ_AWS_ACCOUNT_ID> (see aws-drift-cleanup-*.md).
# To re-include a class, pass UNTAGGED_EXCLUDE="" or a narrower pattern.
# ---------------------------------------------------------------------------
UNTAGGED_EXCLUDE="${UNTAGGED_EXCLUDE:-:stack/amplify-|arn:aws:payments::}"

# Transform a get-resources response into findings, tagging each with its region.
# Service name is ARN field 3 (arn:partition:service:..).
transform() {
  jq --arg required "$REQUIRED_TAGS" --arg region "$1" --arg exclude "$UNTAGGED_EXCLUDE" '
    ($required | split(" ")) as $need
    | [ .ResourceTagMappingList[]
        | { arn: .ResourceARN, present: [ .Tags[].Key ] }
        | { region: $region,
            arn,
            service: (.arn | split(":")[2]),
            missing: ($need - .present) }
        | select(.missing | length > 0)
        | select($exclude == "" or (.arn | test($exclude) | not)) ]'
}

if [[ "$MOCK" == "1" ]]; then
  findings="$(aws_json tagged-resources resourcegroupstaggingapi get-resources \
    | transform us-east-1)"
else
  findings="[]"
  for region in $REGIONS; do
    part="$(aws_region "$region" resourcegroupstaggingapi get-resources \
      | transform "$region")"
    findings="$(jq -s 'add' <(printf '%s' "$findings") <(printf '%s' "$part"))"
  done
fi

emit_check untagged "$findings"
