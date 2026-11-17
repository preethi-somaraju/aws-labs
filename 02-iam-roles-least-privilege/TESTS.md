# Lab 02 — Test results

Account `<redacted>`, us-east-1, 2026-11-16. All output is real command output,
trimmed only for width. Account IDs replaced with `<account-id>`.

Two stages. Policy simulation answers "would this be allowed" without creating
anything; real calls under assumed sessions then confirm the simulator and
reality agree. Disagreement between them would itself be the finding.

## Stage 1 — `iam simulate-principal-policy`

| # | Principal | Action | Resource | Expected | Actual | Status |
|---|-----------|--------|----------|----------|--------|--------|
| S1 | engineer | `s3:PutObject` | `raw/` | allowed | allowed | Pass |
| S2 | engineer | `s3:PutObject` | `curated/` | allowed | allowed | Pass |
| S3 | engineer | `s3:GetObject` | `analytics/` | allowed | allowed | Pass |
| S4 | engineer | `s3:PutObject` | `analytics/` | explicitDeny | explicitDeny | Pass |
| S5 | engineer | `iam:CreateUser` | `*` | explicitDeny | explicitDeny | Pass |
| S6 | analyst | `s3:GetObject` | `curated/` | allowed | allowed | Pass |
| S7 | analyst | `s3:PutObject` | `analytics/` | allowed | allowed | Pass |
| S8 | analyst | `s3:GetObject` | `raw/` | explicitDeny | explicitDeny | Pass |
| S9 | analyst | `s3:PutObject` | `curated/` | implicitDeny | implicitDeny | Pass |
| S10 | analyst | `iam:AttachRolePolicy` | `*` | explicitDeny | explicitDeny | Pass |

S8 and S9 are the pair worth reading together. Writing to `curated/` is an
**implicitDeny** — no statement allows it, so it fails by default. Reading
`raw/` is an **explicitDeny** — a Deny statement fires. The difference matters:
an implicit deny is reversed the moment any later policy grants the action; an
explicit deny is not.

S5 and S10 are the permissions boundary. Neither role's identity policy
mentions IAM at all; the boundary is what produces the deny.

## Stage 2 — real calls under assumed sessions

| # | Principal | Action | Expected | Actual | Status |
|---|-----------|--------|----------|--------|--------|
| R1 | engineer | write `raw/sample.txt` | succeeds | succeeded | Pass |
| R2 | engineer | write `curated/sample.txt` | succeeds | succeeded | Pass |
| R3 | engineer | write `analytics/bad.txt` | AccessDenied | AccessDenied | Pass |
| R4 | analyst | read `curated/sample.txt` | succeeds | succeeded | Pass |
| R5 | analyst | write `analytics/result.csv` | succeeds | succeeded | Pass |
| R6 | analyst | read `raw/sample.txt` | denied | AccessDenied, explicit | Pass |
| R7 | analyst | list `raw/` | denied | AccessDenied | Pass |
| R8 | analyst | no object retrieved in R6 | no file written | no file written | Pass |

### R6 — the evidence that matters

```
$ aws s3api get-object --bucket lab-data-lake-<account-id> \
    --key raw/sample.txt /tmp/leak.txt

An error occurred (AccessDenied) when calling the GetObject operation:
User: arn:aws:sts::<account-id>:assumed-role/lab-data-analyst/ana-raw is not
authorized to perform: s3:GetObject on resource:
"arn:aws:s3:::lab-data-lake-<account-id>/raw/sample.txt"
with an explicit deny in an identity-based policy
```

AWS names the mechanism itself: *with an explicit deny in an identity-based
policy*. That is the design working, not merely an absence of permission.

### R7 — denied before any object is touched

```
$ aws s3 ls s3://lab-data-lake-<account-id>/raw/
An error occurred (AccessDenied) when calling the ListObjectsV2 operation: Access Denied
```

The `s3:prefix` condition on `ListBucket` means the analyst cannot enumerate
`raw/` at all. Without that condition the role could list object keys — which
leak schema, volume and naming — while still being unable to read them.

## Issue found during testing

**A negative test reported a false failure.**

*Symptom.* R6 first came back as a FAIL from the harness:

```
fatal error: An error occurred (403) when calling the HeadObject operation: Forbidden
```

The assertion was looking for the string `AccessDenied` and did not find it.

*Root cause.* `aws s3 cp` issues a `HeadObject` before the `GET`. A denied HEAD
returns a bare `403 Forbidden` with no reason attached — S3 deliberately does
not explain why on a HEAD. The access *was* correctly denied; the assertion was
too narrow.

*Resolution.* Re-ran the same check with `aws s3api get-object`, which performs
the GET directly and returns the full reason, including `with an explicit deny
in an identity-based policy`. Also verified no file had been written to disk in
either attempt.

*Why it is recorded.* This is the mirror of the usual trap. The familiar
failure is a test that passes for the wrong reason; this one failed for the
wrong reason, and taking it at face value would have meant debugging a policy
that was already correct. For IAM work specifically: the high-level `aws s3`
commands tell you *that* something failed, and `aws s3api` tells you *what*
stopped it.

## Cleanup verification

```
$ terraform destroy
$ python scripts/verify_torn_down.py
```

Result recorded in the write-up. Publication is blocked until it returns clean.
