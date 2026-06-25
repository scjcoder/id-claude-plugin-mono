###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the GitLab OIDC federation template.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

output "role_arn" {
  description = "ARN of the GitLab CI role. Set as AWS_ROLE_ARN in CI/CD variables."
  value       = aws_iam_role.gitlab_ci.arn
}

output "role_name" {
  description = "Name of the GitLab CI role."
  value       = aws_iam_role.gitlab_ci.name
}

output "oidc_provider_arn" {
  description = "ARN of the GitLab OIDC provider in use."
  value       = local.oidc_provider_arn
}
