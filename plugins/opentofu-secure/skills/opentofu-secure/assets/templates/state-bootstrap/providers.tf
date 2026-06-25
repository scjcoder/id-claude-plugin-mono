###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : AWS provider for the state-bootstrap config (self-contained).
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }

  skip_metadata_api_check     = false
  skip_region_validation      = false
  skip_credentials_validation = false

  retry_mode  = "adaptive"
  max_retries = 5
}

locals {
  tags = merge(
    {
      Project     = var.project_name
      Environment = "shared"
      Owner       = var.owner
      ManagedBy   = "OpenTofu"
      Purpose     = "tofu-remote-state"
    },
    var.common_tags,
  )
}

data "aws_caller_identity" "current" {}
