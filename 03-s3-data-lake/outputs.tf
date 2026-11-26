output "lake_bucket" {
  value = aws_s3_bucket.lake.id
}

output "zones" {
  value = [for k in aws_s3_object.zone : k.key]
}
