resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "opentofu_state" {
  bucket = "gitops-page-tfstate-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_versioning" "opentofu_state" {
  bucket = aws_s3_bucket.opentofu_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "opentofu_state" {
  bucket = aws_s3_bucket.opentofu_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "opentofu_state" {
  bucket                  = aws_s3_bucket.opentofu_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
