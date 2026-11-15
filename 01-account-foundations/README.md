# Lab 01 — Account Foundations

**Cost: $0.** A budget, an S3 bucket holding a few KB, and a DynamoDB table
billed per request. Nothing here runs continuously.

## What this builds

Three things, in the order a real account should get them:

1. **A budget alarm** at $5/month, alerting at 50% actual and 100% forecast
2. **An S3 bucket for Terraform state** — versioned, encrypted, public access blocked
3. **A DynamoDB table for state locking**

## Why these first

Nothing else in this repo exists yet, and that is the point.

The budget comes first because the expensive AWS mistakes are not dramatic —
they are quiet. A NAT Gateway left running costs about $32/month and does not
announce itself. An alert at 50% of a $5 ceiling means I find out while it is
still $2.50.

Remote state comes next because local state is a single point of failure. The
file on my laptop is the only record of what Terraform believes exists; lose it
and Terraform will cheerfully try to create resources that are already there.
Versioning on the bucket means I can roll back a corrupted state file. The lock
table stops two applies running at once — unlikely with one person, but it is
the habit that matters.

Public access block on the state bucket is not optional. State files contain
resource IDs, ARNs, sometimes secrets.

## Running it

```bash
cp terraform.tfvars.example terraform.tfvars   # set your alert email
terraform init
terraform plan
terraform apply
```

## Verify

```bash
# Budget exists
aws budgets describe-budgets --account-id "$(terraform output -raw account_id)" \
  --query 'Budgets[].{Name:BudgetName,Limit:BudgetLimit.Amount}' --output table

# State bucket refuses public access
aws s3api get-public-access-block --bucket "$(terraform output -raw state_bucket)"

# Lock table is on-demand, not provisioned
aws dynamodb describe-table --table-name "$(terraform output -raw lock_table)" \
  --query 'Table.BillingModeSummary.BillingMode' --output text
```

Expect `BlockPublicAcls: true` on all four settings and `PAY_PER_REQUEST` on
the table. Check the email for the budget confirmation.

## Using this state in later labs

Later labs point at the bucket this one created:

```hcl
terraform {
  backend "s3" {
    bucket         = "aws-labs-tfstate-<account-id>"
    key            = "02-vpc-networking/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "aws-labs-tflock"
    encrypt        = true
  }
}
```

## Teardown

This lab stays up — later labs depend on the state bucket. To remove it all:

```bash
terraform destroy
```

S3 will refuse to delete a versioned bucket that still has object versions, so
empty it first (`aws s3 rm s3://<bucket> --recursive`) and delete the remaining
versions, or the destroy fails partway.

## Notes

The chicken-and-egg problem: this lab creates the state bucket, so it cannot
store its own state in it. Its state stays local. That is normal — most teams
bootstrap the backend exactly this way and never migrate the bootstrap itself.
