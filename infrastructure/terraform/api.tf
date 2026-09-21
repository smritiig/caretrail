resource "aws_apigatewayv2_api" "caretrail" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "ingestion" {
  api_id = aws_apigatewayv2_api.caretrail.id

  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ingestion.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "audit_events" {
  api_id = aws_apigatewayv2_api.caretrail.id

  route_key = "POST /audit-events"
  target    = "integrations/${aws_apigatewayv2_integration.ingestion.id}"

  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.caretrail.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.caretrail.id
  name   = "$default"

  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.api_throttling_burst_limit
    throttling_rate_limit  = var.api_throttling_rate_limit
  }
}

resource "aws_lambda_permission" "api_gateway_ingestion" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.caretrail.execution_arn}/*/*"
}