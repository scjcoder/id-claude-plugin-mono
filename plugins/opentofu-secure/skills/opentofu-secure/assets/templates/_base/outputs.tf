###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Common outputs available in every config (account/region context).
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

output "account_id" {
  description = "AWS account ID this config is deployed into."
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS region this config is deployed into."
  value       = data.aws_region.current.name
}

output "name_prefix" {
  description = "Computed <project>-<environment> naming prefix."
  value       = local.name_prefix
}
