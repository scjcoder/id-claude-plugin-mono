###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : GitLab.com -> AWS OIDC federation. Keyless CI auth with a
#               least-privilege role whose trust policy is pinned to STABLE
#               identifiers (namespace_id + project_id), not the reusable path.
# Last updated: 2026-06-21
# Version     : 1.0.0
#
# WHY the id pinning matters: on GitLab.com SaaS a deleted group/project PATH can
# be reclaimed by another user. A trust policy keyed only on the path-based `sub`
# claim could then be assumed by an unintended actor. namespace_id/project_id are
# never reused, so we condition on them. (AWS IAM + GitLab joint guidance.)
###############################################################################

# Create the IdP once per account. Set create_oidc_provider = false to reuse one.
resource "aws_iam_openid_connect_provider" "gitlab" {
  count = var.create_oidc_provider ? 1 : 0

  url            = "https://${var.gitlab_host}"
  client_id_list = ["https://${var.gitlab_host}"]

  # GitLab.com rotates certs; thumbprint is no longer validated by STS for
  # well-known IdPs, but the field is still required by the API.
  thumbprint_list = var.gitlab_thumbprints

  tags = { Name = "${var.gitlab_host}-oidc" }
}

locals {
  oidc_provider_arn = var.create_oidc_provider ? aws_iam_openid_connect_provider.gitlab[0].arn : var.existing_oidc_provider_arn
}

data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    # Audience must equal the configured aud in id_tokens.
    condition {
      test     = "StringEquals"
      variable = "${var.gitlab_host}:aud"
      values   = ["https://${var.gitlab_host}"]
    }

    # STABLE identifiers — the security-critical conditions.
    condition {
      test     = "StringEquals"
      variable = "${var.gitlab_host}:namespace_id"
      values   = [var.gitlab_namespace_id]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.gitlab_host}:project_id"
      values   = [var.gitlab_project_id]
    }

    # Constrain which refs/pipelines may assume the role (path-based, for scope).
    condition {
      test     = "StringLike"
      variable = "${var.gitlab_host}:sub"
      values   = var.allowed_subjects
    }
  }
}

resource "aws_iam_role" "gitlab_ci" {
  name                 = "${local.name_prefix}-gitlab-ci"
  description          = "GitLab CI OIDC role for ${var.project_name} (${var.environment})"
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  max_session_duration = var.max_session_duration
  permissions_boundary = var.permissions_boundary_arn

  tags = { Name = "${local.name_prefix}-gitlab-ci" }
}

# Least-privilege inline permissions. Replace the example with real actions.
data "aws_iam_policy_document" "permissions" {
  statement {
    sid       = "TofuStateAccess"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.state_bucket}/${var.project_name}/*"]
  }

  statement {
    sid       = "TofuStateList"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.state_bucket}"]
  }
}

resource "aws_iam_role_policy" "permissions" {
  name   = "${local.name_prefix}-permissions"
  role   = aws_iam_role.gitlab_ci.id
  policy = data.aws_iam_policy_document.permissions.json
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each = toset(var.managed_policy_arns)

  role       = aws_iam_role.gitlab_ci.name
  policy_arn = each.value
}
