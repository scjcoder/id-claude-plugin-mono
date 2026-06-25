###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the state-bootstrap config.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

variable "project_name" {
  description = "Project/account label used in tags (the state bucket is account-wide)."
  type        = string
  default     = "platform"
}

variable "aws_region" {
  description = "Region for the state bucket. One bucket per account+region."
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Owning person or team for tagging."
  type        = string
  default     = "sean.johnson@insidedesk.com"
}

variable "common_tags" {
  description = "Extra tags merged on top of the managed defaults."
  type        = map(string)
  default     = {}
}
