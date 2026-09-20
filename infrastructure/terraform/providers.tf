provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CareTrail"
      Environment = "development"
      ManagedBy   = "Terraform"
    }
  }
}