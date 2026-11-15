output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "state_bucket" {
  description = "Set as the backend bucket in later labs"
  value       = aws_s3_bucket.state.id
}

output "lock_table" {
  value = aws_dynamodb_table.lock.name
}
