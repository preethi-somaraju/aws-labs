# Lab 03 — Test results

Account `<lab-account>` (the `aws-labs` member account, not the management
account), us-east-1, 2026-11-26. Bucket `lab-lake-e8459b4d`.

All output below is real command output from `tests.sh` and `tests-legacy.sh`,
trimmed only for width. Account IDs replaced with `<account-id>`. The harness
wraps the CLI in a shell function that appends `--profile preethi-labs
--region us-east-1`; the command lines are otherwise exactly as run.

Thirteen checks, all passing. A check that failed for a reason other than the
expected one is reported as a failure, not a pass — lab 02 lost an hour to a
negative test that was denied correctly and asserted wrongly, and the harness
now encodes that distinction.

| # | Case | Expected | Actual | Status |
|---|------|----------|--------|--------|
| 1 | write into `raw/` | succeeds | 200, `ServerSideEncryption: AES256` | Pass |
| 2 | write to `scratch/` | AccessDenied | AccessDenied, explicit, resource-based | Pass |
| 3 | plain upload under the legacy SSE statement | AccessDenied | AccessDenied | Pass |
| 4 | upload with `--server-side-encryption AES256` | succeeds | succeeded | Pass |
| 4b | upload with `aws:kms` | AccessDenied | AccessDenied | Pass |
| 5 | `head-object` on a headerless upload | `AES256` | `AES256` | Pass |
| 6 | request over plain HTTP | AccessDenied | AccessDenied | Pass |
| 7 | overwrite a curated object | 2 versions | 2 versions | Pass |
| 8 | read the replaced version | original content | `first version` | Pass |
| 9 | delete, then read | delete marker, `NoSuchKey` | 1 marker, `NoSuchKey` | Pass |
| 10 | abandoned multipart upload | invisible to `ls`, visible to `list-multipart-uploads` | exactly that | Pass |
| 11 | read an object in `DEEP_ARCHIVE` | InvalidObjectState | InvalidObjectState | Pass |
| 12 | lifecycle configuration | four named rules | four named rules | Pass |

## 2 — the layout is enforced, not documented

```
$ aws s3api put-object --bucket lab-lake-e8459b4d --key scratch/oops.csv \
    --body events.csv

An error occurred (AccessDenied) when calling the PutObject operation:
User: arn:aws:sts::<account-id>:assumed-role/OrganizationAccountAccessRole/...
is not authorized to perform: s3:PutObject on resource:
"arn:aws:s3:::lab-lake-e8459b4d/scratch/oops.csv"
with an explicit deny in a resource-based policy
```

Note *resource-based*. Lab 02's denials all read *identity-based*: they
described what a role was allowed to do. This one is attached to the bucket
and applies to every caller, including the identity running Terraform.

## 3 and 5 — the encryption policy that no longer does anything

The widely copied statement denies any PUT that does not carry an SSE header.
Applied, it does exactly that:

```
$ aws s3api put-object --bucket lab-lake-e8459b4d \
    --key raw/dt=2026-11-26/plain.csv --body events.csv

An error occurred (AccessDenied) when calling the PutObject operation:
... with an explicit deny in a resource-based policy
```

And here is the object uploaded in case 1, by a command that sent no such
header, while that statement was not in force:

```
$ aws s3api head-object --bucket lab-lake-e8459b4d \
    --key raw/dt=2026-11-26/events.csv --query ServerSideEncryption
AES256
```

The data was encrypted either way. Since January 2023 S3 encrypts every object
at rest whether the caller asks or not, so that statement no longer decides
whether data is encrypted — only whether clients that did not think to send a
header get a 403.

What replaces it enforces the *algorithm* instead, and needs two conditions
rather than one:

```hcl
condition {
  test     = "Null"
  variable = "s3:x-amz-server-side-encryption"
  values   = ["false"]          # the header must be present
}
condition {
  test     = "StringNotEquals"
  variable = "s3:x-amz-server-side-encryption"
  values   = ["AES256"]         # and must say AES256
}
```

The `Null` test is not decoration. `StringNotEquals` against a key that is
absent evaluates to **true**, so without it the statement would deny every
caller that simply did not send the header — reintroducing the bug it was
written to remove. Case 4b confirms a mismatched algorithm is still refused:

```
$ aws s3api put-object --key curated/wrong.csv --server-side-encryption aws:kms
An error occurred (AccessDenied) ... with an explicit deny in a resource-based policy
```

## 7, 8, 9 — versioning

```
versions listed: 2
current:  second version
restored: first version
delete markers: 1
```

```
$ aws s3api get-object --bucket lab-lake-e8459b4d --key curated/report.txt out.txt
An error occurred (NoSuchKey) when calling the GetObject operation:
The specified key does not exist.
```

The object is not gone — a delete marker is now the current version, and the
data sits behind it. `NoSuchKey` here means "no current version", which is a
different claim from "no object". Removing the marker restores the file.

## 10 — storage you are paying for that a listing will not show

A multipart upload was started, one 5 MiB part uploaded, and the upload never
completed:

```
$ aws s3 ls s3://lab-lake-e8459b4d/raw/dt=2026-11-26/
2026-11-26 17:04:05         32 events.csv

$ aws s3api list-multipart-uploads --bucket lab-lake-e8459b4d
------------------------------------------------------------
|                   ListMultipartUploads                   |
+----------------------------+-----------------------------+
|          Initiated         |             Key             |
+----------------------------+-----------------------------+
|  2026-11-26T23:05:12+00:00 |  raw/dt=2026-11-26/big.bin  |
+----------------------------+-----------------------------+
```

The 5 MiB part is billed as storage. It appears in no object listing, in no
bucket size shown by `s3 ls --summarize`, and in no inventory of objects,
because it is not an object yet. Only `list-multipart-uploads` sees it. This is
why the lifecycle configuration carries an `abort-orphaned-parts` rule that
needs no prefix and protects every zone.

## 11 — a lifecycle choice is a readability choice

```
$ aws s3api get-object --key raw/dt=2026-11-26/cold.csv cold.csv

An error occurred (InvalidObjectState) when calling the GetObject operation:
The operation is not valid for the object's storage class

Additional error details:
StorageClass: DEEP_ARCHIVE
```

Deep Archive is roughly four times cheaper than Glacier Instant Retrieval and
cannot be read at all without a restore that takes hours. Had `raw/` been
given a Deep Archive transition at 90 days, every reprocessing job older than
a quarter would fail exactly like this, and the lifecycle rule that caused it
would be three months in the past. `GLACIER_IR` is the choice that keeps the
data readable.

## 12 — the rules are the ones that were designed

```
$ aws s3api get-bucket-lifecycle-configuration --bucket lab-lake-e8459b4d \
    --query 'Rules[].ID'
raw-cooling   curated-history   analytics-disposable   abort-orphaned-parts
```

## Not tested here

Transitions themselves. A 30-day transition cannot be observed in an afternoon,
and S3 gives no way to simulate the passage of time. What is verified is that
the configuration AWS stores matches the configuration that was written — the
transition behaviour itself is taken on documented behaviour, and the lab says
so rather than implying it was watched.
