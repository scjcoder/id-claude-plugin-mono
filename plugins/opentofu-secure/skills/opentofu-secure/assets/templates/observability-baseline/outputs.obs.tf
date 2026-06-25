###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the observability baseline template (CloudWatch + Config).
# Last updated: 2026-06-22
# Version     : 1.1.0
###############################################################################

output "log_group_name" {
  description = "Name of the encrypted CloudWatch log group."
  value       = aws_cloudwatch_log_group.this.name
}

output "alerts_topic_arn" {
  description = "SNS topic ARN for alarms/notifications."
  value       = aws_sns_topic.alerts.arn
}

output "config_recorder_name" {
  description = "AWS Config recorder name (null if Config disabled)."
  value       = var.enable_config ? aws_config_configuration_recorder.this[0].name : null
}
