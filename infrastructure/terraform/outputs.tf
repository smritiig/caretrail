output "audit_queue_url" {
  description = "URL of the audit-event SQS queue"
  value       = aws_sqs_queue.audit_queue.url
}

output "audit_queue_arn" {
  description = "ARN of the audit-event SQS queue"
  value       = aws_sqs_queue.audit_queue.arn
}

output "audit_dlq_url" {
  description = "URL of the audit dead-letter queue"
  value       = aws_sqs_queue.audit_dlq.url
}

output "audit_table_name" {
  description = "Name of the DynamoDB audit table"
  value       = aws_dynamodb_table.audit_events.name
}

output "api_endpoint" {
  description = "CareTrail HTTP API endpoint"
  value       = aws_apigatewayv2_api.caretrail.api_endpoint
}
output "cognito_user_pool_id" {
  description = "CareTrail Cognito user pool ID"
  value       = aws_cognito_user_pool.caretrail.id
}

output "cognito_client_id" {
  description = "CareTrail Cognito application client ID"
  value       = aws_cognito_user_pool_client.caretrail.id
}