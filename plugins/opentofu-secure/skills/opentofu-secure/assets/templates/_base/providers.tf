###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : AWS provider config with mandatory default tags + safe defaults.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

provider "aws" {
  region = var.aws_region

  # Every resource that supports tagging inherits these. Resource-level tags
  # merge on top (see tags.tf -> local.tags).
  default_tags {
    tags = local.tags
  }

  # Fail loudly instead of silently using bad/empty credentials or regions.
  skip_metadata_api_check     = false
  skip_region_validation      = false
  skip_credentials_validation = false

  retry_mode  = "adaptive"
  max_retries = 5
}

# Aliased us-east-1 provider for global resources (ACM for CloudFront, etc.).
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.tags
  }

  skip_metadata_api_check     = false
  skip_region_validation      = false
  skip_credentials_validation = false

  retry_mode  = "adaptive"
  max_retries = 5
}
