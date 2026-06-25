###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : Outputs for the Lambda + HTTP API template.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

output "lambda_function_name" {
  description = "Name of the Lambda function."
  value       = aws_lambda_function.this.function_name
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role (extend its inline policy for app perms)."
  value       = aws_iam_role.lambda.arn
}

output "api_endpoint" {
  description = "Invoke URL of the HTTP API stage."
  value       = aws_apigatewayv2_stage.this.invoke_url
}
