output "cloudfront_url" {
  description = "Public URL of the deployment status page"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "api_url" {
  description = "Full URL of the /today endpoint"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/today"
}

output "s3_bucket_name" {
  description = "S3 bucket holding the frontend files"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidations"
  value       = aws_cloudfront_distribution.frontend.id
}

output "github_actions_role_arn" {
  description = "Paste this as AWS_ROLE_ARN in GitHub repository secrets"
  value       = aws_iam_role.github_actions.arn
}
