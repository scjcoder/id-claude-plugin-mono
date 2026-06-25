###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Common input variables shared by every config (the scaffold).
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

variable "project_name" {
  description = "Short, lowercase project identifier used in resource names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}[a-z0-9]$", var.project_name))
    error_message = "project_name must be lowercase alphanumeric/hyphen, 3-32 chars, no leading/trailing hyphen."
  }
}

variable "environment" {
  description = "Deployment environment. Drives naming, retention, and guardrails."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "Primary AWS region for regional resources."
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Owning person or team. Required for traceability tagging."
  type        = string
  default     = "sean.johnson@insidedesk.com"
}

variable "common_tags" {
  description = "Extra tags merged on top of the managed defaults. Keep keys PascalCase."
  type        = map(string)
  default     = {}
}
