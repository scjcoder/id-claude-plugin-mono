###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Hardened S3 bucket — KMS encryption, versioning, TLS-only,
#               public access fully blocked, lifecycle transitions.
# Last updated: 2026-06-22
# Version     : 1.1.0
###############################################################################

# --- KMS key dedicated to this bucket (rotation on) -------------------------
resource "aws_kms_key" "bucket" {
  count = var.s3_create_kms_key ? 1 : 0

  description             = "${local.name_prefix}-${var.bucket_suffix} S3 encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  tags = { Name = "${local.name_prefix}-${var.bucket_suffix}-s3" }
}

resource "aws_kms_alias" "bucket" {
  count = var.s3_create_kms_key ? 1 : 0

  name          = "alias/${local.name_prefix}-${var.bucket_suffix}-s3"
  target_key_id = aws_kms_key.bucket[0].key_id
}

locals {
  # Use the dedicated key if created, otherwise a caller-supplied key, else SSE-S3.
  s3_kms_key_arn = var.s3_create_kms_key ? aws_kms_key.bucket[0].arn : var.s3_kms_key_arn
  sse_algo       = local.s3_kms_key_arn != null ? "aws:kms" : "AES256"
}

# --- Bucket -----------------------------------------------------------------
resource "aws_s3_bucket" "this" {
  bucket = "${local.name_prefix}-${var.bucket_suffix}"

  tags = { Name = "${local.name_prefix}-${var.bucket_suffix}" }
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Block every avenue of public access. Non-negotiable default.
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server access logging to a dedicated log bucket. Off by default to avoid coupling;
# set log_target_bucket for an auditable access trail (recommended for prod data).
resource "aws_s3_bucket_logging" "this" {
  count = var.log_target_bucket != null ? 1 : 0

  bucket        = aws_s3_bucket.this.id
  target_bucket = var.log_target_bucket
  target_prefix = "s3-access/${local.name_prefix}-${var.bucket_suffix}/"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = local.sse_algo
      kms_master_key_id = local.s3_kms_key_arn
    }
    bucket_key_enabled = local.sse_algo == "aws:kms"
  }
}

# Deny non-TLS and unencrypted-PUT requests at the bucket policy layer.
data "aws_iam_policy_document" "bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.this.arn,
      "${aws_s3_bucket.this.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid       = "DenyUnEncryptedObjectUploads"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = [local.sse_algo]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.bucket.json

  # Policy that blocks public access must land after the access block exists.
  depends_on = [aws_s3_bucket_public_access_block.this]
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "transition-and-expire-noncurrent"
    status = "Enabled"

    filter {}

    transition {
      days          = var.transition_ia_days
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = var.transition_ia_days
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_expiration_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
