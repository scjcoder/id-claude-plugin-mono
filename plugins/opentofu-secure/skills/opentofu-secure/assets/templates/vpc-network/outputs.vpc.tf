###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the VPC network template.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

output "vpc_id" {
  description = "ID of the created VPC."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets keyed insertion order."
  value       = [for s in aws_subnet.public : s.id]
}

output "private_subnet_ids" {
  description = "IDs of the private subnets."
  value       = [for s in aws_subnet.private : s.id]
}

output "nat_gateway_id" {
  description = "NAT gateway ID (null when disabled)."
  value       = var.enable_nat_gateway ? aws_nat_gateway.this[0].id : null
}
