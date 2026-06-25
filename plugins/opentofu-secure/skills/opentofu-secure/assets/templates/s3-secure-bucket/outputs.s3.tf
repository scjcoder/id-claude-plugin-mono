###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the hardened S3 bucket template.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

output "bucket_id" {
  description = "Name of the created S3 bucket."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN of the created S3 bucket."
  value       = aws_s3_bucket.this.arn
}

output "bucket_kms_key_arn" {
  description = "KMS key ARN protecting the bucket (null if SSE-S3)."
  value       = local.s3_kms_key_arn
}
