###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the observability baseline template (CloudWatch + Config).
# Last updated: 2026-06-22
# Version     : 1.1.0
###############################################################################

variable "alert_emails" {
  description = "Email addresses subscribed to the SNS alert topic."
  type        = list(string)
  default     = []
}

variable "enable_billing_alarm" {
  description = "Create the estimated-charges billing alarm (us-east-1 metric)."
  type        = bool
  default     = true
}

variable "billing_alarm_threshold_usd" {
  description = "USD threshold for the billing alarm."
  type        = number
  default     = 100
}

variable "enable_config" {
  description = "Enable AWS Config recorder + baseline rules."
  type        = bool
  default     = true
}

variable "config_log_bucket" {
  description = "Existing S3 bucket name for AWS Config snapshots (required if enable_config)."
  type        = string
  default     = ""
}
