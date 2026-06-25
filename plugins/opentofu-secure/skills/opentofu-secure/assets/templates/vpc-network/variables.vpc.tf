###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the VPC network template.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

variable "vpc_cidr" {
  description = "CIDR block for the VPC (a /16 gives room for the /20 subnet split)."
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid CIDR block."
  }
}

variable "az_count" {
  description = "Number of AZs to spread subnets across (2-3 typical)."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 1 && var.az_count <= 4
    error_message = "az_count must be between 1 and 4."
  }
}

variable "enable_nat_gateway" {
  description = "Create a single NAT gateway for private-subnet egress (adds hourly cost)."
  type        = bool
  default     = false
}
