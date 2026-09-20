resource "aws_iam_role" "verification_lambda" {
  name               = "${var.project_name}-verification-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "verification_logs" {
  role       = aws_iam_role.verification_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "verification_access" {
  name = "${var.project_name}-verification-access"
  role = aws_iam_role.verification_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = aws_dynamodb_table.audit_events.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.audit_archive.arn}/*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "verification_lambda" {
  name              = "/aws/lambda/${var.project_name}-verification"
  retention_in_days = 7
}

resource "aws_lambda_function" "verification" {
  function_name = "${var.project_name}-verification"
  role          = aws_iam_role.verification_lambda.arn
  runtime       = "python3.13"
  handler       = "src.handlers.verify_event.lambda_handler"

  filename         = local.lambda_package
  source_code_hash = filebase64sha256(local.lambda_package)

  memory_size = 256
  timeout     = 15

  environment {
    variables = {
      AUDIT_TABLE_NAME  = aws_dynamodb_table.audit_events.name
      AUDIT_BUCKET_NAME = aws_s3_bucket.audit_archive.id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.verification_logs,
    aws_iam_role_policy.verification_access,
    aws_cloudwatch_log_group.verification_lambda
  ]
}

resource "aws_apigatewayv2_integration" "verification" {
  api_id = aws_apigatewayv2_api.caretrail.id

  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.verification.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "verify_audit_event" {
  api_id = aws_apigatewayv2_api.caretrail.id

  route_key = "GET /audit-events/{event_id}/verify"
  target    = "integrations/${aws_apigatewayv2_integration.verification.id}"

  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.caretrail.id
}

resource "aws_lambda_permission" "api_gateway_verification" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verification.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.caretrail.execution_arn}/*/GET/audit-events/*/verify"
}