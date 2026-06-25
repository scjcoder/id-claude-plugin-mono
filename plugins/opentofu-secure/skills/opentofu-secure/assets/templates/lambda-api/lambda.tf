###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Lambda function with a least-privilege execution role, a
#               KMS-encrypted log group, and X-Ray-free defaults. No WAF.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

resource "aws_kms_key" "lambda" {
  description             = "${local.name_prefix} lambda logs/env encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.lambda_kms.json

  tags = { Name = "${local.name_prefix}-lambda" }
}

data "aws_iam_policy_document" "lambda_kms" {
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

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name_prefix}"
  retention_in_days = var.environment == "prod" ? 365 : 30
  kms_key_id        = aws_kms_key.lambda.arn

  tags = { Name = "${local.name_prefix}-lambda" }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name_prefix}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = { Name = "${local.name_prefix}-lambda" }
}

# Least-privilege: only write to this function's own log group.
data "aws_iam_policy_document" "lambda_logs" {
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_logs" {
  name   = "${local.name_prefix}-lambda-logs"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_logs.json
}

resource "aws_lambda_function" "this" {
  function_name = local.name_prefix
  role          = aws_iam_role.lambda.arn
  handler       = var.handler
  runtime       = var.runtime
  filename      = var.package_path
  timeout       = var.timeout
  memory_size   = var.memory_size

  # Reserve concurrency to cap blast radius / cost when set (>= 0).
  reserved_concurrent_executions = var.reserved_concurrency

  kms_key_arn = aws_kms_key.lambda.arn

  dynamic "environment" {
    for_each = length(var.environment_variables) > 0 ? [1] : []
    content {
      variables = var.environment_variables
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = { Name = local.name_prefix }
}
