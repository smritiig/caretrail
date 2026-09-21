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

variable "api_throttling_rate_limit" {
  description = "Target API Gateway requests per second"
  type        = number
  default     = 2

  validation {
    condition = (
      var.api_throttling_rate_limit > 0 &&
      var.api_throttling_rate_limit <= 100
    )
    error_message = "API throttling rate must be between 0 and 100."
  }
}

variable "api_throttling_burst_limit" {
  description = "Target API Gateway burst capacity"
  type        = number
  default     = 5

  validation {
    condition = (
      var.api_throttling_burst_limit >= 1 &&
      var.api_throttling_burst_limit <= 100
    )
    error_message = "API throttling burst must be between 1 and 100."
  }
}