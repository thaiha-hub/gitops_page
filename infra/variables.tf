variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-north-1"
}

variable "github_repo" {
  description = "GitHub repository in org/repo format, used for OIDC trust policy"
  type        = string
}
