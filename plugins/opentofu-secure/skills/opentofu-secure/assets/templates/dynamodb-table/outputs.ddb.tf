###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the DynamoDB table template.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

output "table_name" {
  description = "Name of the DynamoDB table."
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table."
  value       = aws_dynamodb_table.this.arn
}

output "table_kms_key_arn" {
  description = "KMS key ARN protecting the table."
  value       = local.ddb_kms_key_arn
}
