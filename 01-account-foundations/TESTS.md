# Lab 01 — Test results

Account `<redacted>`, us-east-1, 2026-11-15. All output below is real
command output, trimmed only for width.

| # | Test case | Expected | Actual | Status |
|---|-----------|----------|--------|--------|
| T1 | Budget exists at the stated limit | $5.00 USD, MONTHLY | $5.0 USD, MONTHLY | Pass |
| T2 | Two notification thresholds | 50% ACTUAL, 100% FORECASTED | both present, GREATER_THAN | Pass |
| T3 | State bucket blocks public access | all four settings true | all four true | Pass |
| T4 | State bucket versioning | Enabled | Enabled | Pass |
| T5 | State bucket encrypted at rest | AES256 | AES256 | Pass |
| T6 | Lock table on-demand billing | PAY_PER_REQUEST | PAY_PER_REQUEST, ACTIVE | Pass |
| N1 | Public bucket policy is rejected | AccessDenied | AccessDenied, cites BlockPublicPolicy | Pass |
| N2 | No policy left attached after N1 | NoSuchBucketPolicy | NoSuchBucketPolicy | Pass |

## Evidence

### T1 / T2 — budget and notifications

```
$ aws budgets describe-budgets --account-id <account> \
    --query 'Budgets[].{Name:BudgetName,Limit:BudgetLimit.Amount,Period:TimeUnit}'
| Limit |       Name         | Period   | Unit   |
|  5.0  |  aws-labs-monthly  |  MONTHLY |  USD   |

$ aws budgets describe-notifications-for-budget --budget-name aws-labs-monthly
|      Op      |  Threshold  |    Type      |
|  GREATER_THAN|  50.0       |  ACTUAL      |
|  GREATER_THAN|  100.0      |  FORECASTED  |
```

### T3 / T4 / T5 — state bucket posture

```
$ aws s3api get-public-access-block --bucket aws-labs-tfstate-<account>
{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
}

$ aws s3api get-bucket-versioning  --bucket ...   -> Enabled
$ aws s3api get-bucket-encryption  --bucket ...   -> AES256
```

### T6 — lock table

```
$ aws dynamodb describe-table --table-name aws-labs-tflock
|   Key  |       Mode        | Status   |
|  LockID|  PAY_PER_REQUEST  |  ACTIVE  |
```

### N1 — public policy rejected

The useful part is *who* was refused. This ran as AdministratorAccess:

```
$ aws s3api put-bucket-policy --bucket aws-labs-tfstate-<account> \
    --policy file://public.json

An error occurred (AccessDenied) when calling the PutBucketPolicy operation:
User: arn:aws:sts::<account>:assumed-role/AWSReservedSSO_AdministratorAccess_.../...
is not authorized to perform: s3:PutBucketPolicy on resource:
"arn:aws:s3:::aws-labs-tfstate-<account>" because public policies are prevented
by the BlockPublicPolicy setting in S3 Block Public Access.
```

Block Public Access sits above identity permissions. An administrator cannot
override it with a policy — the setting has to be turned off first, which is a
separate, auditable action.

### N2 — nothing left behind

```
$ aws s3api get-bucket-policy --bucket aws-labs-tfstate-<account>
An error occurred (NoSuchBucketPolicy) ... The bucket policy does not exist
```

## Issue hit during testing

**Symptom.** N1 first returned `ParamValidation: Unable to load paramfile
file:///tmp/public.json`.

**Root cause.** The shell was Git Bash but `aws` is the native Windows
executable, which does not resolve the MSYS `/tmp` path.

**Resolution.** Used `file://C:/tmp/public.json`.

**Why it is recorded.** The first run failed for a reason unrelated to the
control being tested. Read quickly it looks like a non-zero exit and could be
mistaken for the policy being blocked — a false pass. A negative test only
counts when the error returned is the error the test is about.

## Screenshots to capture

Console evidence to add under `screenshots/`:

| Title | Where | Should show |
|-------|-------|-------------|
| `budget-overview.png` | Billing → Budgets → aws-labs-monthly | $5 limit, 50%/100% alerts, current spend |
| `budget-alert-email.png` | Email inbox | The AWS budget confirmation email |
| `s3-block-public-access.png` | S3 → bucket → Permissions | All four settings On |
| `dynamodb-lock-table.png` | DynamoDB → Tables → aws-labs-tflock | On-demand capacity, ACTIVE |
