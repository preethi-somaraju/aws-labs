#!/usr/bin/env bash
# Lab 03 — twelve cases against the live bucket. Run after terraform apply:
#
#     bash tests.sh 2>&1 | tee /c/tmp/lab03/results.txt
#
# A case that fails for a reason other than the expected one is reported as a
# failure, not a pass. Lab 02 lost an hour to a negative test that was denied
# correctly and asserted wrongly.
set -uo pipefail

AWS="/c/Program Files/Amazon/AWSCLIV2/aws.exe"
PROFILE=preethi-labs
REGION=us-east-1
WORK=/c/tmp/lab03
WORK_WIN=C:/tmp/lab03

mkdir -p "$WORK"
B=$(terraform output -raw lake_bucket)
echo "bucket: $B"
echo

pass=0; fail=0; notes=()

ok()  { pass=$((pass+1)); echo "  PASS"; echo; }
bad() { fail=$((fail+1)); echo "  FAIL — $1"; notes+=("$2: $1"); echo; }

# check <label> <ok|deny> <pattern-when-deny> -- <command...>
check() {
  local label="$1" mode="$2" want="$3"; shift 4
  echo "=== $label"
  printf '$ %s\n' "$(printf '%q ' "$@" | sed 's#/c/Program Files/Amazon/AWSCLIV2/aws.exe#aws#')"
  local out rc
  out=$("$@" 2>&1); rc=$?
  echo "$out" | sed 's/[0-9]\{12\}/<account-id>/g'
  if [ "$mode" = ok ]; then
    [ $rc -eq 0 ] && ok || bad "exit $rc, expected success" "$label"
  else
    if [ $rc -eq 0 ]; then
      bad "succeeded; a denial was expected" "$label"
    elif printf '%s' "$out" | grep -q "$want"; then
      ok
    else
      bad "denied, but not with '$want' — wrong reason" "$label"
    fi
  fi
}

a() { "$AWS" "$@" --profile "$PROFILE" --region "$REGION"; }

printf 'event,ts\n1,2026-11-26T00:00:00Z\n' > "$WORK/events.csv"
printf 'first version\n' > "$WORK/v1.txt"
printf 'second version\n' > "$WORK/v2.txt"
head -c 5242880 /dev/urandom > "$WORK/part.bin"   # 5 MiB: the multipart minimum

# ---------------------------------------------------------------- the layout
check "1. write into raw/" ok "" -- \
  a s3api put-object --bucket "$B" --key raw/dt=2026-11-26/events.csv --body "$WORK_WIN/events.csv"

check "2. write outside the zones" deny "AccessDenied" -- \
  a s3api put-object --bucket "$B" --key scratch/oops.csv --body "$WORK_WIN/events.csv"

# ------------------------------------------------------------- encryption
check "5. default encryption applied without being asked" ok "" -- \
  a s3api head-object --bucket "$B" --key raw/dt=2026-11-26/events.csv

check "4. explicit AES256 accepted" ok "" -- \
  a s3api put-object --bucket "$B" --key curated/events.csv --body "$WORK_WIN/events.csv" \
    --server-side-encryption AES256

check "4b. a different algorithm refused" deny "AccessDenied" -- \
  a s3api put-object --bucket "$B" --key curated/wrong.csv --body "$WORK_WIN/events.csv" \
    --server-side-encryption aws:kms

check "6. request over plain HTTP" deny "AccessDenied" -- \
  a s3api list-objects-v2 --bucket "$B" --endpoint-url "http://s3.$REGION.amazonaws.com"

# ------------------------------------------------------------- versioning
echo "=== 7. overwrite a curated object, then count versions"
a s3api put-object --bucket "$B" --key curated/report.txt --body "$WORK_WIN/v1.txt" >/dev/null
V1=$(a s3api list-object-versions --bucket "$B" --prefix curated/report.txt \
       --query 'Versions[0].VersionId' --output text)
a s3api put-object --bucket "$B" --key curated/report.txt --body "$WORK_WIN/v2.txt" >/dev/null
N=$(a s3api list-object-versions --bucket "$B" --prefix curated/report.txt \
      --query 'length(Versions)' --output text)
echo "versions listed: $N"
[ "$N" = "2" ] && ok || bad "expected 2 versions, got $N" "7. versioning"

echo "=== 8. read the version the overwrite replaced"
a s3api get-object --bucket "$B" --key curated/report.txt --version-id "$V1" \
  "$WORK_WIN/restored.txt" >/dev/null 2>&1
echo "current:  $(a s3 cp "s3://$B/curated/report.txt" - 2>/dev/null)"
echo "restored: $(cat "$WORK/restored.txt")"
grep -q "first version" "$WORK/restored.txt" && ok || bad "previous version not recoverable" "8. version read"

echo "=== 9. delete leaves a marker, not a hole"
a s3api delete-object --bucket "$B" --key curated/report.txt >/dev/null
MARKERS=$(a s3api list-object-versions --bucket "$B" --prefix curated/report.txt \
            --query 'length(DeleteMarkers)' --output text)
GETOUT=$(a s3api get-object --bucket "$B" --key curated/report.txt "$WORK_WIN/gone.txt" 2>&1)
echo "delete markers: $MARKERS"
echo "$GETOUT" | sed 's/[0-9]\{12\}/<account-id>/g'
if [ "$MARKERS" = "1" ] && printf '%s' "$GETOUT" | grep -q "NoSuchKey"; then ok
else bad "expected 1 marker and NoSuchKey on read" "9. delete marker"; fi

# -------------------------------------------------- the storage you cannot see
echo "=== 10. an abandoned multipart upload"
UP=$(a s3api create-multipart-upload --bucket "$B" --key raw/dt=2026-11-26/big.bin \
       --query UploadId --output text)
a s3api upload-part --bucket "$B" --key raw/dt=2026-11-26/big.bin \
  --upload-id "$UP" --part-number 1 --body "$WORK_WIN/part.bin" >/dev/null
echo '$ aws s3 ls s3://'"$B"'/raw/dt=2026-11-26/'
a s3 ls "s3://$B/raw/dt=2026-11-26/"
echo '$ aws s3api list-multipart-uploads --bucket '"$B"
a s3api list-multipart-uploads --bucket "$B" \
  --query 'Uploads[].{Key:Key,Initiated:Initiated}' --output table
LISTED=$(a s3 ls "s3://$B/raw/dt=2026-11-26/" | grep -c "big.bin")
PARTS=$(a s3api list-multipart-uploads --bucket "$B" --query 'length(Uploads)' --output text)
if [ "$LISTED" = "0" ] && [ "$PARTS" = "1" ]; then ok
else bad "ls showed $LISTED, list-multipart-uploads showed $PARTS" "10. orphaned parts"; fi
a s3api abort-multipart-upload --bucket "$B" --key raw/dt=2026-11-26/big.bin --upload-id "$UP"

# ------------------------------------------------------------- lifecycle
echo "=== 11. read an object in DEEP_ARCHIVE"
a s3api put-object --bucket "$B" --key raw/dt=2026-11-26/cold.csv   --body "$WORK_WIN/events.csv" --storage-class DEEP_ARCHIVE >/dev/null
echo '$ aws s3api get-object --key raw/dt=2026-11-26/cold.csv cold.csv'
COLD=$(a s3api get-object --bucket "$B" --key raw/dt=2026-11-26/cold.csv          "$WORK_WIN/cold.csv" 2>&1); rc=$?
echo "$COLD" | sed 's/[0-9]\{12\}/<account-id>/g'
if [ $rc -eq 0 ]; then
  bad "the read succeeded; Deep Archive should need a restore first" "11. deep archive"
elif printf '%s' "$COLD" | grep -q "InvalidObjectState"; then
  ok
else
  bad "failed, but not with InvalidObjectState — wrong reason" "11. deep archive"
fi

echo "=== 12. lifecycle configuration as designed"
RULES=$(a s3api get-bucket-lifecycle-configuration --bucket "$B" \
          --query 'Rules[].ID' --output text)
echo "rules: $RULES"
missing=""
for r in raw-cooling curated-history analytics-disposable abort-orphaned-parts; do
  printf '%s' "$RULES" | grep -q "$r" || missing="$missing $r"
done
[ -z "$missing" ] && ok || bad "missing rules:$missing" "12. lifecycle"

# ------------------------------------------------------------------ summary
echo "================================"
echo "passed: $pass   failed: $fail"
for n in "${notes[@]:-}"; do [ -n "$n" ] && echo "  - $n"; done
[ "$fail" -eq 0 ] || exit 1
