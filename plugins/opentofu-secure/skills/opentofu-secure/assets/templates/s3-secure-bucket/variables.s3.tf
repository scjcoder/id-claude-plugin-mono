###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the hardened S3 bucket template.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

variable "bucket_suffix" {
  description = "Suffix appended to <project>-<env>- to form the bucket name."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,40}[a-z0-9]$", var.bucket_suffix))
    error_message = "bucket_suffix must be lowercase DNS-safe (a-z, 0-9, hyphen)."
  }
}

variable "s3_create_kms_key" {
  description = "Create a dedicated, rotating KMS key for this bucket."
  type        = bool
  default     = true
}

variable "s3_kms_key_arn" {
  description = "Existing KMS key ARN to use when s3_create_kms_key = false. Null = SSE-S3."
  type        = string
  default     = null
}

variable "transition_ia_days" {
  description = "Days before current/noncurrent objects transition to STANDARD_IA."
  type        = number
  default     = 90
}

variable "noncurrent_expiration_days" {
  description = "Days before noncurrent object versions are permanently deleted."
  type        = number
  default     = 365
}

variable "log_target_bucket" {
  description = "Existing log bucket for S3 server access logs. Null disables logging."
  type        = string
  default     = null
}
