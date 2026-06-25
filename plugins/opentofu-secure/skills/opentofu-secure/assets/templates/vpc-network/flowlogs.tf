###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : VPC flow logs to a KMS-encrypted CloudWatch log group, with a
#               least-privilege delivery role. Required for network forensics.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

resource "aws_kms_key" "flow_logs" {
  description             = "${local.name_prefix} VPC flow logs encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.flow_logs_kms.json

  tags = { Name = "${local.name_prefix}-flowlogs" }
}

data "aws_iam_policy_document" "flow_logs_kms" {
  statement {
    sid       = "AccountAdmin"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${data.aws_region.current.name}.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/vpc/${local.name_prefix}/flow-logs"
  retention_in_days = var.environment == "prod" ? 365 : 30
  kms_key_id        = aws_kms_key.flow_logs.arn

  tags = { Name = "${local.name_prefix}-flowlogs" }
}

data "aws_iam_policy_document" "flow_logs_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "flow_logs" {
  name               = "${local.name_prefix}-flow-logs"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume.json

  tags = { Name = "${local.name_prefix}-flow-logs" }
}

data "aws_iam_policy_document" "flow_logs_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["${aws_cloudwatch_log_group.flow_logs.arn}:*"]
  }
}

resource "aws_iam_role_policy" "flow_logs" {
  name   = "${local.name_prefix}-flow-logs"
  role   = aws_iam_role.flow_logs.id
  policy = data.aws_iam_policy_document.flow_logs_permissions.json
}

resource "aws_flow_log" "this" {
  vpc_id                   = aws_vpc.this.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.flow_logs.arn
  iam_role_arn             = aws_iam_role.flow_logs.arn
  max_aggregation_interval = 600

  tags = { Name = "${local.name_prefix}-flow-log" }
}
