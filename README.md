# AWS Data Engineering Labs — 52 Weeks

One lab a week, building AWS data engineering depth: ingestion, storage,
transformation, orchestration, warehousing and governance. Terraform for
everything, tested with real output, documented, torn down.

Background: 10+ years in data engineering and analytics — SQL, Python, ETL,
Azure Data Factory. These labs build the AWS half properly, in public.

## How each lab works

Design → implement → test → document → clean up. A successful `terraform apply`
proves nothing; every lab records positive and negative tests with actual
output. Problems hit along the way are written up as they happened.

**No NAT Gateway** unless a lab is about it — private subnets reach AWS
services through VPC endpoints. A budget alarm exists from week 1.

## Phase 1 — Foundations for data work (weeks 1–6)

| Wk | Lab | Proves |
|----|-----|--------|
| 01 | Account foundations | Cost guardrails exist before any resource does |
| 02 | IAM for data access | Analysts and engineers reach different prefixes, provably |
| 03 | S3 as a data lake | Zone layout survives contact with real queries |
| 04 | KMS & Secrets Manager | Data encrypted at rest; no credential in a job definition |
| 05 | VPC for data services | Glue and Redshift reach S3 with no internet path |
| 06 | Cost allocation | Spend attributable per pipeline, not per account |

## Phase 2 — Lake & catalog (weeks 7–14)

| Wk | Lab | Proves |
|----|-----|--------|
| 07 | Partitioning strategy | Partition layout decides what a query costs |
| 08 | File formats & compression | Parquet vs CSV vs JSON measured, not assumed |
| 09 | Glue Data Catalog & crawlers | Schema discovery, and where crawlers get it wrong |
| 10 | Athena fundamentals | Bytes scanned is the unit that matters |
| 11 | Athena tuning | Partition projection and CTAS against a real query |
| 12 | Apache Iceberg on S3 | Table format gives ACID and time travel on a lake |
| 13 | Lake Formation | Permissions at table and column level, not bucket level |
| 14 | Glue Data Quality | Bad data caught before it reaches a consumer |

## Phase 3 — Batch ETL (weeks 15–22)

| Wk | Lab | Proves |
|----|-----|--------|
| 15 | Glue PySpark jobs | Spark on managed infrastructure, and what DPUs cost |
| 16 | Glue bookmarks | Incremental loads that do not reprocess everything |
| 17 | Dynamic frames & schema drift | A new upstream column does not break the job |
| 18 | EMR Serverless | When Spark outgrows Glue, and the cost crossover |
| 19 | Lambda ETL | Small transforms without a Spark cluster, and the limits |
| 20 | dbt on Fargate | SQL transformations with tests and lineage |
| 21 | Schema evolution | Readers survive added, renamed and retyped columns |
| 22 | Idempotency & reprocessing | A rerun produces the same table, not double rows |

## Phase 4 — Streaming (weeks 23–30)

| Wk | Lab | Proves |
|----|-----|--------|
| 23 | Kinesis Data Streams | Shards, ordering, and what backpressure looks like |
| 24 | Firehose to S3 | Buffering trade-off between latency and small files |
| 25 | Managed Flink | Windowed aggregation on a live stream |
| 26 | MSK | Kafka semantics and when it beats Kinesis |
| 27 | Glue Schema Registry | Producers cannot ship a breaking schema |
| 28 | CDC with DMS | Database changes land in the lake without full reloads |
| 29 | Streaming into Iceberg | Continuous ingest with queryable, compacted tables |
| 30 | Exactly-once & dedup | At-least-once delivery handled honestly |

## Phase 5 — Warehousing & serving (weeks 31–38)

| Wk | Lab | Proves |
|----|-----|--------|
| 31 | Redshift Serverless | Warehouse without capacity planning, and what it bills for |
| 32 | Distribution & sort keys | Key choice decides join performance |
| 33 | Redshift Spectrum | Querying the lake from the warehouse |
| 34 | COPY, UNLOAD, WLM | Bulk load patterns and queue management |
| 35 | RDS as a source | OLTP workload feeding analytics without hurting it |
| 36 | DynamoDB serving layer | Low-latency reads over aggregated results |
| 37 | OpenSearch | Log and text analytics the warehouse handles badly |
| 38 | Dimensional modelling | Star schema on Redshift, and SCD Type 2 in practice |

## Phase 6 — Orchestration (weeks 39–44)

| Wk | Lab | Proves |
|----|-----|--------|
| 39 | Step Functions for ETL | Orchestration with explicit retry and failure paths |
| 40 | MWAA fundamentals | Managed Airflow, and what it costs idle |
| 41 | DAG patterns | Dependencies, sensors, and avoiding scheduler traps |
| 42 | Event-driven pipelines | EventBridge triggering work on arrival, not on a clock |
| 43 | Failure handling & alerting | A failed pipeline is noticed before a consumer notices |
| 44 | Backfills & late data | Reprocessing a window without corrupting the present |

## Phase 7 — Governance, BI & ML (weeks 45–50)

| Wk | Lab | Proves |
|----|-----|--------|
| 45 | QuickSight | BI on Athena and Redshift, including refresh cost |
| 46 | Lineage & metadata | Tracing a column back to its source |
| 47 | PII detection & masking | Macie findings and column-level redaction |
| 48 | SageMaker Feature Store | Training and serving read the same features |
| 49 | Bedrock for data | LLM enrichment and classification in a pipeline |
| 50 | Data contracts | Producers break consumers loudly, at the boundary |

## Phase 8 — Operations & capstone (weeks 51–52)

| Wk | Lab | Proves |
|----|-----|--------|
| 51 | Pipeline observability & cost | Freshness, volume and spend on one dashboard |
| 52 | Capstone lakehouse | Ingest → transform → warehouse → BI, orchestrated and monitored |

## Layout

```
NN-lab-name/
  DESIGN.md     design, approved before anything is created
  *.tf          Terraform
  TESTS.md      test cases with actual recorded output
  BLOG.md       the write-up
  docs/blog/screenshots/
```

## Cost and teardown

Every lab states its cost before the first command and ends with
`terraform destroy`. Redshift, MSK, MWAA and OpenSearch are the expensive
ones; those labs state the hourly rate up front and run briefly.

Destroy is verified, not assumed:

```bash
terraform destroy
python scripts/verify_torn_down.py    # non-zero if anything survived
```

It checks resources tagged `Project=aws-labs` and, separately, the services
that bill whether tagged or not — EC2, NAT gateways, Elastic IPs, RDS, load
balancers, Redshift, MSK, MWAA, OpenSearch. Lab 01's budget, state bucket and
lock table are permanent and allowed; anything else is a finding.

No lab is published until this returns clean.

## Figures

Terminal figures are photographs of a real terminal, not typeset cards. The
commands are echoed by bash under `set -x`, so a figure cannot show one command
and run another, and the `.sh` that produced each one is committed beside it in
`docs/blog/commands/`. Before any window opens the output is scanned for
account IDs, access keys and personal paths; if anything matches, nothing is
captured — changing the command is the fix, not redacting the picture.

Bucket names use a random suffix rather than the account ID, so nothing has to
be redacted out of plan and apply output in the first place.
