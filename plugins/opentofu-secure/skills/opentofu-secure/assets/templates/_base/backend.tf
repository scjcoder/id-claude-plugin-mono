###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Remote state on S3 with native S3 state locking (no DynamoDB).
# Last updated: 2026-06-21
# Version     : 1.0.0
#
# Partial configuration: the bucket/key/region are passed at init time so the
# same code can target dev vs prod without edits, e.g.
#
#   tofu init \
#     -backend-config="bucket=<account>-tfstate-<region>" \
#     -backend-config="key=<project>/<environment>/terraform.tfstate" \
#     -backend-config="region=us-east-1"
#
# See backend.<env>.hcl for committed, reviewable per-environment values.
###############################################################################

terraform {
  backend "s3" {
    encrypt = true

    # Native S3 locking (OpenTofu/Terraform 1.10+). Replaces dynamodb_table.
    use_lockfile = true
  }
}
