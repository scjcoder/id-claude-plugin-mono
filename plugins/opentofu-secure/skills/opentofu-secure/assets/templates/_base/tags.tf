###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Single source of truth for the mandatory tag set (traceability).
# Last updated: 2026-06-21
# Version     : 1.0.0
###############################################################################

locals {
  # Mandatory tags applied via provider default_tags. Resource-specific tags
  # should merge on top of local.tags, never replace it.
  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "OpenTofu"
    },
    var.common_tags,
  )

  # Name prefix convention reused across resources: <project>-<env>.
  name_prefix = "${var.project_name}-${var.environment}"
}
