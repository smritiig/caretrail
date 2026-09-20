locals {
  lambda_package = "${path.module}/../../build/caretrail-lambda.zip"
}

resource "aws_cloudwatch_log_group" "ingestion_lambda" {
  name              = "/aws/lambda/${var.project_name}-ingestion"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "worker_lambda" {
  name              = "/aws/lambda/${var.project_name}-worker"
  retention_in_days = 7
}

resource "aws_lambda_function" "ingestion" {
  function_name = "${var.project_name}-ingestion"
  role          = aws_iam_role.ingestion_lambda.arn
  runtime       = "python3.13"
  handler       = "src.handlers.ingest_event.lambda_handler"

  filename         = local.lambda_package
  source_code_hash = filebase64sha256(local.lambda_package)

  memory_size = 256
  timeout     = 10


  environment {
    variables = {
      AUDIT_QUEUE_URL = aws_sqs_queue.audit_queue.url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.ingestion_logs,
    aws_cloudwatch_log_group.ingestion_lambda
  ]
}

resource "aws_lambda_function" "worker" {
  function_name = "${var.project_name}-worker"
  role          = aws_iam_role.worker_lambda.arn
  runtime       = "python3.13"
  handler       = "src.handlers.process_event.lambda_handler"

  filename         = local.lambda_package
  source_code_hash = filebase64sha256(local.lambda_package)

  memory_size = 256
  timeout     = 30


  environment {
    variables = {
      AUDIT_TABLE_NAME  = aws_dynamodb_table.audit_events.name
      AUDIT_BUCKET_NAME = aws_s3_bucket.audit_archive.id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.worker_logs,
    aws_iam_role_policy.worker_access,
    aws_cloudwatch_log_group.worker_lambda
  ]
}

resource "aws_lambda_event_source_mapping" "audit_queue" {
  event_source_arn = aws_sqs_queue.audit_queue.arn
  function_name    = aws_lambda_function.worker.arn

  batch_size                         = 10
  enabled                            = true
  function_response_types            = ["ReportBatchItemFailures"]
  maximum_batching_window_in_seconds = 1

  scaling_config {
    maximum_concurrency = 2
  }

  depends_on = [
    aws_iam_role_policy.worker_access
  ]
}