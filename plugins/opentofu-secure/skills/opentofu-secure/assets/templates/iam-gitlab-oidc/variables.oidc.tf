###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the GitLab OIDC federation template.
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

variable "gitlab_host" {
  description = "GitLab host (OIDC issuer without scheme)."
  type        = string
  default     = "gitlab.com"
}

variable "create_oidc_provider" {
  description = "Create the GitLab IdP. Set false to reuse an existing one per account."
  type        = bool
  default     = true
}

variable "existing_oidc_provider_arn" {
  description = "ARN of an existing GitLab IdP, used when create_oidc_provider = false."
  type        = string
  default     = null
}

variable "gitlab_thumbprints" {
  description = "Root CA thumbprints for the IdP cert chain."
  type        = list(string)
  default     = ["b3dd7606d2b5a8b4a13771dbecc9ee1cecafa38a"]
}

variable "gitlab_namespace_id" {
  description = "STABLE GitLab namespace (group) ID. Find via group Settings or API."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.gitlab_namespace_id))
    error_message = "gitlab_namespace_id must be the numeric ID, not the group path."
  }
}

variable "gitlab_project_id" {
  description = "STABLE GitLab project ID. Shown on the project's main page / Settings > General."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.gitlab_project_id))
    error_message = "gitlab_project_id must be the numeric ID, not the project path."
  }
}

variable "allowed_subjects" {
  description = "Allowed `sub` patterns scoping which refs/pipelines may assume the role."
  type        = list(string)
  default     = ["project_path:*:ref_type:branch:ref:main"]
}

variable "max_session_duration" {
  description = "Max assumed-role session duration in seconds (3600-43200)."
  type        = number
  default     = 3600
}

variable "permissions_boundary_arn" {
  description = "Optional permissions boundary to cap the role's effective permissions."
  type        = string
  default     = null
}

variable "state_bucket" {
  description = "Tofu state bucket the CI role may read/write for this project."
  type        = string
}

variable "managed_policy_arns" {
  description = "Managed policy ARNs to attach. Keep minimal; prefer the inline policy."
  type        = list(string)
  default     = []
}
