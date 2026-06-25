###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the Route53 + ACM template.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

output "certificate_arn" {
  description = "ARN of the validated ACM certificate."
  value       = aws_acm_certificate_validation.this.certificate_arn
}

output "zone_id" {
  description = "Route53 hosted zone ID used for records."
  value       = data.aws_route53_zone.this.zone_id
}

output "app_record_fqdns" {
  description = "FQDNs of the created application records."
  value       = [for r in aws_route53_record.app : r.fqdn]
}
