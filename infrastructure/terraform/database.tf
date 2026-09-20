resource "aws_dynamodb_table" "audit_events" {
  name         = "${var.project_name}-audit-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}