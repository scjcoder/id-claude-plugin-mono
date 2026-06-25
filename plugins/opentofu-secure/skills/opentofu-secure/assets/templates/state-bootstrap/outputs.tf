###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the state-bootstrap config.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

output "state_bucket" {
  description = "Name of the remote state bucket. Use in backend.<env>.hcl `bucket`."
  value       = aws_s3_bucket.state.id
}

output "state_kms_key_arn" {
  description = "KMS key ARN encrypting the state bucket."
  value       = aws_kms_key.state.arn
}
