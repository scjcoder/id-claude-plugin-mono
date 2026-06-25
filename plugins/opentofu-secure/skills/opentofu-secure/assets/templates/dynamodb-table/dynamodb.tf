###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : DynamoDB table — customer-managed KMS encryption, point-in-time
#               recovery, on-demand billing, deletion protection, optional TTL.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

resource "aws_kms_key" "table" {
  count = var.ddb_create_kms_key ? 1 : 0

  description             = "${local.name_prefix}-${var.table_suffix} DynamoDB key"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  tags = { Name = "${local.name_prefix}-${var.table_suffix}-ddb" }
}

locals {
  table_name      = "${local.name_prefix}-${var.table_suffix}"
  ddb_kms_key_arn = var.ddb_create_kms_key ? aws_kms_key.table[0].arn : var.ddb_kms_key_arn
}

resource "aws_dynamodb_table" "this" {
  name         = local.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = var.hash_key
  range_key    = var.range_key

  deletion_protection_enabled = var.deletion_protection

  dynamic "attribute" {
    for_each = var.attributes
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = local.ddb_kms_key_arn
  }

  point_in_time_recovery {
    enabled = true
  }

  dynamic "ttl" {
    for_each = var.ttl_attribute != null ? [1] : []
    content {
      attribute_name = var.ttl_attribute
      enabled        = true
    }
  }

  tags = { Name = local.table_name }
}
