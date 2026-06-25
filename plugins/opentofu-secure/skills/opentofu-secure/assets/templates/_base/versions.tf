###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Pin OpenTofu/Terraform core and provider versions.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

terraform {
  # 1.10+ (and OpenTofu 1.10+) is required for S3 native state locking
  # (use_lockfile) so we can drop the DynamoDB lock table entirely.
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}
