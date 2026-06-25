###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : ACM certificate with DNS validation + Route53 records, fully
#               automated (no manual validation steps). us-east-1 aliased
#               provider so the cert is usable by CloudFront.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

data "aws_route53_zone" "this" {
  name         = var.zone_name
  private_zone = false
}

# Cert is issued in us-east-1 so it is valid for both regional services and
# CloudFront (which only accepts certs from us-east-1).
resource "aws_acm_certificate" "this" {
  provider = aws.us_east_1

  domain_name               = var.domain_name
  subject_alternative_names = var.subject_alternative_names
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = { Name = var.domain_name }
}

# One validation record per distinct domain on the cert.
resource "aws_route53_record" "validation" {
  for_each = {
    for dvo in aws_acm_certificate.this.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id         = data.aws_route53_zone.this.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "this" {
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.this.arn
  validation_record_fqdns = [for r in aws_route53_record.validation : r.fqdn]
}

# Application alias/CNAME records (e.g. pointing at CloudFront or an ALB).
resource "aws_route53_record" "app" {
  for_each = var.app_records

  zone_id = data.aws_route53_zone.this.zone_id
  name    = each.key
  type    = each.value.type

  # Alias record when alias_target is set; otherwise a standard record.
  dynamic "alias" {
    for_each = each.value.alias_target != null ? [each.value.alias_target] : []
    content {
      name                   = alias.value.dns_name
      zone_id                = alias.value.zone_id
      evaluate_target_health = alias.value.evaluate_target_health
    }
  }

  ttl     = each.value.alias_target == null ? each.value.ttl : null
  records = each.value.alias_target == null ? each.value.records : null
}
