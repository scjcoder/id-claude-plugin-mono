###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the Route53 + ACM template.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

variable "zone_name" {
  description = "Existing public hosted zone name, e.g. scj.net."
  type        = string
}

variable "domain_name" {
  description = "Primary fully-qualified domain for the certificate."
  type        = string
}

variable "subject_alternative_names" {
  description = "Additional SANs (e.g. [\"*.app.scj.net\"]) on the certificate."
  type        = list(string)
  default     = []
}

variable "app_records" {
  description = <<-EOT
    Map of application DNS records keyed by FQDN. For an alias record set
    alias_target; for a standard record set records + ttl and leave alias_target null.
  EOT
  type = map(object({
    type    = string
    ttl     = optional(number, 300)
    records = optional(list(string))
    alias_target = optional(object({
      dns_name               = string
      zone_id                = string
      evaluate_target_health = optional(bool, false)
    }))
  }))
  default = {}
}
