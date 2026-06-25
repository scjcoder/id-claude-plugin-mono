###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : CloudWatch baseline — KMS-encrypted log group with env-based
#               retention, a CMK-encrypted SNS alert topic, and a metric alarm.
# Last updated: 2026-06-22
# Version     : 1.1.0
###############################################################################

# Customer-managed key shared by CloudWatch Logs and the SNS alert topic. Using a
# CMK (not the AWS-managed alias/aws/sns) keeps key management and access auditable.
resource "aws_kms_key" "baseline" {
  description             = "${local.name_prefix} baseline encryption key (logs + SNS)"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  policy = data.aws_iam_policy_document.baseline_kms.json

  tags = { Name = "${local.name_prefix}-baseline" }
}

data "aws_iam_policy_document" "baseline_kms" {
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

  statement {
    sid    = "AllowSNS"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/${var.project_name}/${var.environment}"
  retention_in_days = var.environment == "prod" ? 365 : 30
  kms_key_id        = aws_kms_key.baseline.arn

  tags = { Name = "${local.name_prefix}-logs" }
}

resource "aws_sns_topic" "alerts" {
  name              = "${local.name_prefix}-alerts"
  kms_master_key_id = aws_kms_key.baseline.id

  tags = { Name = "${local.name_prefix}-alerts" }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  for_each = toset(var.alert_emails)

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

# Example alarm: estimated charges. Replace/duplicate for real app metrics.
resource "aws_cloudwatch_metric_alarm" "billing" {
  count = var.enable_billing_alarm ? 1 : 0

  alarm_name          = "${local.name_prefix}-estimated-charges"
  alarm_description   = "Estimated account charges exceeded threshold."
  namespace           = "AWS/Billing"
  metric_name         = "EstimatedCharges"
  statistic           = "Maximum"
  period              = 21600
  evaluation_periods  = 1
  threshold           = var.billing_alarm_threshold_usd
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  dimensions          = { Currency = "USD" }
}
