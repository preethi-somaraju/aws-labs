output "lake_bucket" {
  value = aws_s3_bucket.lake.id
}

output "log_bucket" {
  value = aws_s3_bucket.logs.id
}

output "engineer_role_arn" {
  value = aws_iam_role.engineer.arn
}

output "analyst_role_arn" {
  value = aws_iam_role.analyst.arn
}
