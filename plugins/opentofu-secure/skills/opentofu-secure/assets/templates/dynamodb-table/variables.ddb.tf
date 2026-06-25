###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the DynamoDB table template.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

variable "table_suffix" {
  description = "Suffix appended to <project>-<env>- to form the table name."
  type        = string
}

variable "hash_key" {
  description = "Partition key attribute name."
  type        = string
}

variable "range_key" {
  description = "Optional sort key attribute name."
  type        = string
  default     = null
}

variable "attributes" {
  description = "Key attribute definitions. Only declare keys/index attributes here."
  type = list(object({
    name = string
    type = string # S | N | B
  }))

  validation {
    condition     = alltrue([for a in var.attributes : contains(["S", "N", "B"], a.type)])
    error_message = "attribute type must be one of S, N, B."
  }
}

variable "ttl_attribute" {
  description = "Attribute holding the TTL epoch; null disables TTL."
  type        = string
  default     = null
}

variable "deletion_protection" {
  description = "Block accidental table deletion. Recommended true for prod data."
  type        = bool
  default     = true
}

variable "ddb_create_kms_key" {
  description = "Create a dedicated rotating KMS key for the table."
  type        = bool
  default     = true
}

variable "ddb_kms_key_arn" {
  description = "Existing KMS key ARN used when ddb_create_kms_key = false."
  type        = string
  default     = null
}
