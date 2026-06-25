###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Inputs for the Lambda + HTTP API template.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

variable "package_path" {
  description = "Path to the built Lambda deployment .zip."
  type        = string
}

variable "handler" {
  description = "Lambda handler entrypoint, e.g. index.handler or app.lambda_handler."
  type        = string
  default     = "index.handler"
}

variable "runtime" {
  description = <<-EOT
    Lambda runtime identifier. Defaults to the latest Node.js LTS on Lambda
    (nodejs24.x). The Node 24 runtime bundles AWS SDK for JavaScript v3 and
    requires async handlers (callback-style handlers were removed).
  EOT
  type        = string
  default     = "nodejs24.x"
}

variable "timeout" {
  description = "Function timeout in seconds."
  type        = number
  default     = 10
}

variable "memory_size" {
  description = "Function memory in MB."
  type        = number
  default     = 256
}

variable "reserved_concurrency" {
  description = "Reserved concurrent executions (-1 = unreserved)."
  type        = number
  default     = -1
}

variable "environment_variables" {
  description = "Environment variables for the function (KMS-encrypted at rest)."
  type        = map(string)
  default     = {}
}

variable "route_key" {
  description = "HTTP API route key, e.g. \"GET /\" or \"$default\" for catch-all."
  type        = string
  default     = "$default"
}

variable "throttling_burst_limit" {
  description = "API stage throttling burst limit."
  type        = number
  default     = 50
}

variable "throttling_rate_limit" {
  description = "API stage throttling steady-state rate (req/s)."
  type        = number
  default     = 100
}
