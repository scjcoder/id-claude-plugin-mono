#!/usr/bin/env bash
###############################################################################
# Author      : Sean Johnson <sean@scj.net>
# Purpose     : Public-access / encryption drift check — S3 buckets without a
#               full public-access block (correlated with Route53 so intentional
#               public sites are distinguished from review candidates), and
#               unencrypted EBS volumes. Report-only.
# Last updated: 2026-06-23
# Version     : 1.2.0
#
# A bucket with an open public-access block that ALSO has a Route53 record
# pointing at it is almost certainly a public website on purpose — flagged
# dns_backed and listed for information. A bucket with NO matching DNS record is
# the real review candidate. Matching is by record-name == bucket OR the record's
# target referencing the bucket name (catches FQDN-named buckets and CNAME/alias
# fronting). CloudFront-fronted buckets may show as review candidates — review
# the short list rather than trusting the classification blindly.
#
# S3 default encryption (SSE-S3) is account-wide, so per-bucket
# get-bucket-encryption is slow and near-always clean — dropped. EBS encryption
# drift is still covered. The public-access calls fan out with xargs -P.
###############################################################################
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$HERE/../lib"
# shellcheck source=../lib/common.sh
source "$LIB/common.sh"

S3_PARALLELISM="${AWS_DRIFT_S3_PARALLELISM:-12}"

# --- S3: full public-access block (parallel, one call per bucket) ------------
gather_s3() {
  local pargs=(); mapfile -t pargs < <(profile_args)
  aws s3api list-buckets "${pargs[@]}" --output json \
    | jq -r '.Buckets[].Name' \
    | xargs -P "$S3_PARALLELISM" -I {} bash "$LIB/s3_bucket_check.sh" {} \
    | jq -s '.'
}

# --- EBS: unencrypted volumes (per region) ----------------------------------
gather_ebs() {
  local acc="[]" region part
  for region in $REGIONS; do
    part="$(aws_region "$region" ec2 describe-volumes \
      | jq --arg region "$region" '[ .Volumes[] | select(.Encrypted == false)
            | {region:$region, type:"ebs-volume", name:.VolumeId,
               issues:["unencrypted volume"]} ]')"
    acc="$(jq -s 'add' <(printf '%s' "$acc") <(printf '%s' "$part"))"
  done
  printf '%s' "$acc"
}

# --- Route53: flatten all records to a {name, target} index ------------------
gather_dns() {
  local pargs=(); mapfile -t pargs < <(profile_args)
  local zones; zones="$(aws route53 list-hosted-zones "${pargs[@]}" \
    --output json | jq -r '.HostedZones[].Id')"
  for zone in $zones; do
    aws route53 list-resource-record-sets --hosted-zone-id "$zone" \
      "${pargs[@]}" --output json
  done | jq -s '[ .[].ResourceRecordSets[]
    | { name: (.Name | ascii_downcase | sub("\\.$"; "")),
        target: (((.AliasTarget.DNSName // "")
                  + " " + ([.ResourceRecords[]?.Value] | join(" ")))
                 | ascii_downcase) } ]'
}

if [[ "$MOCK" == "1" ]]; then
  s3="$(aws_json drift-s3 true)"
  ebs="$(aws_json drift-ebs true)"
  dns="$(aws_json drift-dns true)"
else
  s3="$(gather_s3)"; ebs="$(gather_ebs)"; dns="$(gather_dns)"
fi

# Annotate each S3 finding with its Route53 correlation.
s3_annotated="$(jq -n --argjson s3 "$s3" --argjson dns "$dns" '
  $s3 | map(
    (.name | ascii_downcase) as $b
    | ([ $dns[] | select(.name == $b or (.target | contains($b))) | .name ]
       | first) as $record
    | . + { region: "global", dns_backed: ($record != null), dns_record: $record }
  )')"

findings="$(jq -n --argjson s3 "$s3_annotated" --argjson ebs "$ebs" '$s3 + $ebs')"
emit_check public-encryption-drift "$findings"
