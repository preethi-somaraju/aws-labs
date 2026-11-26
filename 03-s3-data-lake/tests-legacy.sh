#!/usr/bin/env bash
# Case 3 — the copy-pasted "deny unencrypted uploads" statement, applied and
# then measured. Flips legacy_sse_deny on, retries a plain upload, flips back.
set -uo pipefail
AWS="/c/Program Files/Amazon/AWSCLIV2/aws.exe"
PROFILE=preethi-labs
REGION=us-east-1
B=$(terraform output -raw lake_bucket)

echo "=== applying the legacy statement"
terraform apply -auto-approve -no-color -input=false -var legacy_sse_deny=true 2>&1 | tail -3
echo

echo '=== 3. plain upload, no SSE header, legacy statement in force'
echo '$ aws s3api put-object --bucket '"$B"' --key raw/plain.csv --body events.csv'
"$AWS" s3api put-object --bucket "$B" --key raw/dt=2026-11-26/plain.csv \
  --body C:/tmp/lab03/events.csv --profile "$PROFILE" --region "$REGION" 2>&1 \
  | sed 's/[0-9]\{12\}/<account-id>/g'
echo

echo '=== the same object, uploaded with the header, is encrypted the same way'
"$AWS" s3api put-object --bucket "$B" --key raw/dt=2026-11-26/asked.csv \
  --body C:/tmp/lab03/events.csv --server-side-encryption AES256 \
  --profile "$PROFILE" --region "$REGION" >/dev/null 2>&1
echo '$ aws s3api head-object --key raw/dt=2026-11-26/events.csv --query ServerSideEncryption'
"$AWS" s3api head-object --bucket "$B" --key raw/dt=2026-11-26/events.csv \
  --query ServerSideEncryption --output text --profile "$PROFILE" --region "$REGION"
echo "  ^ that object was uploaded in case 1 with no header at all"
echo

echo "=== reverting"
terraform apply -auto-approve -no-color -input=false 2>&1 | tail -3
