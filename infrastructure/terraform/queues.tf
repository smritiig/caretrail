resource "aws_sqs_queue" "audit_dlq" {
  name = "${var.project_name}-audit-dlq"

  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "audit_queue" {
  name = "${var.project_name}-audit-events"

  visibility_timeout_seconds = 181
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.audit_dlq.arn
    maxReceiveCount     = 5
  })
}