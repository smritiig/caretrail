variable "aws_region" {
  description = "AWS region used for CareTrail resources"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Name used as a prefix for AWS resources"
  type        = string
  default     = "caretrail"
}