# Lab 03 — S3 as a data lake

Week 3 of 52. Approved before anything was created.

## What this proves

The zone layout from lab 02 survives contact with real objects: writes land
only where the layout allows, old versions are recoverable, and the lifecycle
rules that make a lake affordable are the same rules that can make it
unreadable.

Lab 02 enforced zones through *identity* policy — who may touch which prefix.
This lab enforces them through *resource* policy and lifecycle, which apply to
every caller including the account root.

## Scope

One bucket, three zones, one lifecycle configuration, one bucket policy.
No Glue, no Athena, no KMS — catalog is week 9, queries are week 10, keys are
week 4. Partitioning is week 7, so dates appear in keys here but nothing
depends on them yet.

## Design decisions

**One bucket, prefixes as zones.** A bucket per zone is the common
alternative. It buys independent policy and replication, and costs a
cross-bucket copy on every promotion plus three sets of settings to keep
aligned. At this size prefixes are the honest choice; the write-up says what
would change that (different retention regimes, different accounts, or
replication to a different region).

**Versioning on, bucket-wide.** A lake's worst day is a pipeline that
overwrites curated data with a bad run. Versioning makes that recoverable.
It also means deletes leave delete markers, and that noncurrent versions bill
until a rule removes them — so versioning without a noncurrent-expiration rule
is a slow leak.

**The layout is enforced, not documented.** A bucket policy denies
`s3:PutObject` anywhere outside the three zones. A naming convention that
nothing checks becomes a bucket with eleven top-level prefixes inside a year.

**Lifecycle per zone, because the zones mean different things.**

| Zone | Rule | Why |
|------|------|-----|
| `raw/` | → `STANDARD_IA` at 30d, → `GLACIER_IR` at 90d | Immutable landing data, read rarely after ingest, kept for reprocessing |
| `curated/` | noncurrent versions expire at 90d | Current version stays hot; history is for recovery, not forever |
| `analytics/` | objects expire at 30d | Query results are derived and disposable |
| all | abort incomplete multipart uploads at 7d | Orphaned parts bill and do not appear in a listing |

**`GLACIER_IR`, not `DEEP_ARCHIVE`, for raw.** Deep Archive is roughly four
times cheaper and makes the data unreadable without a restore that takes
hours. A negative test puts an object in Deep Archive and tries to read it, to
show what that choice does to a reader. Lifecycle is a readability decision
before it is a cost decision.

**No lifecycle transitions on small objects.** Each transition is a billed
request, and Glacier classes add about 40 KB of metadata per object. A lake of
10 KB files moved to Glacier costs more after the move than before. Zones here
are sized to make the rule sensible, and the write-up carries the arithmetic.

## The encryption policy this lab deliberately gets wrong first

The widely copied "deny unencrypted uploads" statement denies any PUT that
does not carry `x-amz-server-side-encryption`:

```json
{ "Effect": "Deny", "Action": "s3:PutObject",
  "Condition": { "Null": { "s3:x-amz-server-side-encryption": "true" } } }
```

Since January 2023 every S3 object is encrypted at rest by default whether the
caller asks or not. So this statement no longer decides whether data is
encrypted — it only decides whether clients that did not think to send a
header get a 403. It is applied here, the resulting failure is recorded, and
then it is replaced with a statement that enforces the *algorithm* rather than
the presence of a header. That is the version worth copying.

## Tests

Twelve cases. Every design claim above becomes one.

| # | Case | Expect |
|---|------|--------|
| 1 | PUT to `raw/` | succeeds |
| 2 | PUT to `scratch/` | AccessDenied — layout enforced |
| 3 | PUT with no SSE header, `Null` policy applied | AccessDenied |
| 4 | same PUT, algorithm policy applied | succeeds |
| 5 | `head-object` on a plain upload | `ServerSideEncryption: AES256` |
| 6 | request over HTTP | AccessDenied — `aws:SecureTransport` |
| 7 | overwrite a curated object | two versions listed |
| 8 | read the previous version | original content returned |
| 9 | delete, then list | delete marker, object recoverable |
| 10 | abandoned multipart upload | invisible to `s3 ls`, visible to `list-multipart-uploads` |
| 11 | GET an object in `DEEP_ARCHIVE` | InvalidObjectState |
| 12 | `get-bucket-lifecycle-configuration` | matches the table above |

## Cost

Under $0.05. A handful of KB-sized objects, a few hundred requests, one Deep
Archive object carrying a 180-day minimum charge on about 1 KB. Destroyed at
the end and the teardown verified.
