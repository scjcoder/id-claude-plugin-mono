###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : AWS Config recorder + delivery channel + baseline managed rules.
#               Records all resource changes for audit/compliance.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

resource "aws_iam_role" "config" {
  count = var.enable_config ? 1 : 0

  name               = "${local.name_prefix}-config"
  assume_role_policy = data.aws_iam_policy_document.config_assume.json

  tags = { Name = "${local.name_prefix}-config" }
}

data "aws_iam_policy_document" "config_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "config" {
  count = var.enable_config ? 1 : 0

  role       = aws_iam_role.config[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

resource "aws_config_configuration_recorder" "this" {
  count = var.enable_config ? 1 : 0

  name     = "${local.name_prefix}-recorder"
  role_arn = aws_iam_role.config[0].arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "this" {
  count = var.enable_config ? 1 : 0

  name           = "${local.name_prefix}-delivery"
  s3_bucket_name = var.config_log_bucket

  depends_on = [aws_config_configuration_recorder.this]
}

resource "aws_config_configuration_recorder_status" "this" {
  count = var.enable_config ? 1 : 0

  name       = aws_config_configuration_recorder.this[0].name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.this]
}

# Baseline managed rules — cheap, high-signal compliance checks.
resource "aws_config_config_rule" "s3_public_read" {
  count = var.enable_config ? 1 : 0

  name = "${local.name_prefix}-s3-no-public-read"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  }

  depends_on = [aws_config_configuration_recorder.this]
}

resource "aws_config_config_rule" "encrypted_volumes" {
  count = var.enable_config ? 1 : 0

  name = "${local.name_prefix}-encrypted-volumes"

  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }

  depends_on = [aws_config_configuration_recorder.this]
}

resource "aws_config_config_rule" "iam_no_admin" {
  count = var.enable_config ? 1 : 0

  name = "${local.name_prefix}-iam-no-inline-admin"

  source {
    owner             = "AWS"
    source_identifier = "IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS"
  }

  depends_on = [aws_config_configuration_recorder.this]
}
