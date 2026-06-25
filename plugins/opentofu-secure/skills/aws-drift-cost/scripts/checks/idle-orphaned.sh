#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Idle / orphaned resource check — unattached Elastic IPs,
#               available (detached) EBS volumes, and running NAT gateways,
#               across every configured region. Report-only; rough monthly cost.
# Last updated: 2026-06-23
# Version     : 1.1.0
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$HERE/../lib/common.sh"

# Rough on-demand monthly costs (USD) for the savings estimate.
EIP_USD="${AWS_DRIFT_EIP_USD:-3.60}"       # unattached EIP, ~730h * $0.005
NAT_USD="${AWS_DRIFT_NAT_USD:-32.40}"      # NAT gateway hourly, ~730h * $0.045
EBS_GB_USD="${AWS_DRIFT_EBS_GB_USD:-0.08}" # gp3 per GB-month

# Findings for a single region (each tagged with that region).
region_findings() {
  local region="$1" addr vol nat
  if [[ "$MOCK" == "1" ]]; then
    addr="$(aws_json addresses true)"
    vol="$(aws_json volumes-available true)"
    nat="$(aws_json nat-gateways true)"
  else
    addr="$(aws_region "$region" ec2 describe-addresses)"
    vol="$(aws_region "$region" ec2 describe-volumes --filters Name=status,Values=available)"
    nat="$(aws_region "$region" ec2 describe-nat-gateways --filter Name=state,Values=available)"
  fi
  local eips volumes nats
  eips="$(printf '%s' "$addr" | jq --arg region "$region" --argjson cost "$EIP_USD" '
    [ .Addresses[] | select(.AssociationId == null)
      | {region:$region, type:"eip-unattached", name:(.PublicIp // .AllocationId),
         reason:"Elastic IP not associated", est_monthly_usd:$cost} ]')"
  volumes="$(printf '%s' "$vol" | jq --arg region "$region" --argjson rate "$EBS_GB_USD" '
    [ .Volumes[]
      | {region:$region, type:"ebs-volume-available", name:.VolumeId,
         reason:"Volume detached (status=available)",
         est_monthly_usd:((.Size // 0) * $rate | (. * 100 | round) / 100)} ]')"
  nats="$(printf '%s' "$nat" | jq --arg region "$region" --argjson cost "$NAT_USD" '
    [ .NatGateways[]
      | {region:$region, type:"nat-gateway", name:.NatGatewayId,
         reason:"NAT gateway running — confirm still needed", est_monthly_usd:$cost} ]')"
  jq -s 'add' <(printf '%s' "$eips") <(printf '%s' "$volumes") <(printf '%s' "$nats")
}

if [[ "$MOCK" == "1" ]]; then
  findings="$(region_findings us-east-1)"
else
  findings="[]"
  for region in $REGIONS; do
    part="$(region_findings "$region")"
    findings="$(jq -s 'add' <(printf '%s' "$findings") <(printf '%s' "$part"))"
  done
fi

emit_check idle-orphaned "$findings"
