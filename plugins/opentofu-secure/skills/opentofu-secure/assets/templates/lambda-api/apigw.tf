###############################################################################
# Author      : Sean Johnson <sean.johnson@insidedesk.com>
# Purpose     : API Gateway v2 (HTTP API) fronting the Lambda — cheaper than
#               REST, with access logging and throttling. No WAF.
# Last updated: 2026-06-22
# Version     : 1.0.0
###############################################################################

resource "aws_apigatewayv2_api" "this" {
  name          = "${local.name_prefix}-http"
  protocol_type = "HTTP"

  tags = { Name = "${local.name_prefix}-http" }
}

resource "aws_cloudwatch_log_group" "apigw" {
  name              = "/aws/apigw/${local.name_prefix}"
  retention_in_days = var.environment == "prod" ? 365 : 30
  kms_key_id        = aws_kms_key.lambda.arn

  tags = { Name = "${local.name_prefix}-apigw" }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.this.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = var.route_key
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.environment
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.throttling_burst_limit
    throttling_rate_limit  = var.throttling_rate_limit
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigw.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  tags = { Name = "${local.name_prefix}-stage" }
}

# Allow only this API to invoke the function.
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
