###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Pin core + providers for the state-bootstrap config.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # LOCAL backend on purpose: this config CREATES the S3 state bucket that every
  # other config uses, so it cannot store its state there until it exists.
  # After apply, optionally migrate this state into the new bucket (see README).
}
