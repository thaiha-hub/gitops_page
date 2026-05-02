output "opentofu_state_bucket" {
  description = "S3 bucket name to use in infra/providers.tf backend configuration"
  value       = aws_s3_bucket.opentofu_state.bucket
}
