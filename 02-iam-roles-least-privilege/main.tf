terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region  = var.region
  profile = var.profile

  default_tags {
    tags = {
      Project   = "aws-labs"
      Lab       = "02-iam-roles-least-privilege"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

# A random suffix, not the account ID. Bucket names end up in plan output,
# CLI logs and screenshots; embedding the account ID there leaks it everywhere
# and makes any terminal capture unpublishable.
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  account = data.aws_caller_identity.current.account_id
  lake    = "lab-data-lake-${random_id.suffix.hex}"
  logs    = "lab-cloudtrail-${random_id.suffix.hex}"
}

# ---------------------------------------------------------------------------
# The lake. Three zones, one bucket.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "lake" {
  bucket        = local.lake
  force_destroy = true # lab bucket; teardown must not need manual emptying
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

# Zone markers. S3 has no real directories, but a zero-byte key makes the
# layout visible in the console and gives the tests something to list against.
resource "aws_s3_object" "zone" {
  for_each = toset(["raw/", "curated/", "analytics/"])
  bucket   = aws_s3_bucket.lake.id
  key      = each.value
  content  = ""
}

# ---------------------------------------------------------------------------
# CloudTrail. Separate bucket: mixing logs with data lets a data-plane
# compromise erase its own evidence.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "logs" {
  bucket        = local.logs
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "logs" {
  statement {
    sid     = "AWSCloudTrailAclCheck"
    actions = ["s3:GetBucketAcl"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    resources = [aws_s3_bucket.logs.arn]
  }

  statement {
    sid     = "AWSCloudTrailWrite"
    actions = ["s3:PutObject"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    resources = ["${aws_s3_bucket.logs.arn}/AWSLogs/${local.account}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs.json
}

# Management events only. Data events bill per event and are the realistic way
# to turn a free lab into a real charge.
resource "aws_cloudtrail" "lab" {
  name                          = "lab-data-access"
  s3_bucket_name                = aws_s3_bucket.logs.id
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  depends_on = [aws_s3_bucket_policy.logs]
}

# ---------------------------------------------------------------------------
# Permissions boundary. The ceiling neither role can exceed, whatever its own
# identity policy says. Without this, a role holding iam:* grants itself more.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "boundary" {
  statement {
    sid       = "DataPlaneWork"
    actions   = ["s3:*", "athena:*", "glue:*", "logs:*", "sts:GetCallerIdentity"]
    resources = ["*"]
  }

  statement {
    sid    = "NoIdentitySelfService"
    effect = "Deny"
    actions = [
      "iam:*",
      "organizations:*",
      "account:*",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "boundary" {
  name   = "lab-data-boundary"
  policy = data.aws_iam_policy_document.boundary.json
}

# ---------------------------------------------------------------------------
# Trust: the account's own principals may assume either role.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account}:root"]
    }
  }
}

# ---------------------------------------------------------------------------
# Engineer: owns raw/ and curated/. Cannot write query results.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "engineer" {
  statement {
    sid       = "ListLakeZones"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.lake.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["raw/*", "curated/*", "analytics/*", "raw/", "curated/", "analytics/", ""]
    }
  }

  statement {
    sid     = "WriteRawAndCurated"
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = [
      "${aws_s3_bucket.lake.arn}/raw/*",
      "${aws_s3_bucket.lake.arn}/curated/*",
    ]
  }

  statement {
    sid       = "ReadAnalytics"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.lake.arn}/analytics/*"]
  }

  # Results belong to whoever ran the query. A pipeline bug must not be able to
  # overwrite them.
  statement {
    sid       = "NoWritingQueryResults"
    effect    = "Deny"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.lake.arn}/analytics/*"]
  }
}

resource "aws_iam_role" "engineer" {
  name                 = "lab-data-engineer"
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  permissions_boundary = aws_iam_policy.boundary.arn
}

resource "aws_iam_role_policy" "engineer" {
  name   = "zone-access"
  role   = aws_iam_role.engineer.id
  policy = data.aws_iam_policy_document.engineer.json
}

# ---------------------------------------------------------------------------
# Analyst: reads curated/, writes query results. Never sees raw/.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "analyst" {
  statement {
    sid       = "ListCuratedAndAnalytics"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.lake.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["curated/*", "analytics/*", "curated/", "analytics/"]
    }
  }

  statement {
    sid       = "ReadCurated"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.lake.arn}/curated/*"]
  }

  statement {
    sid       = "WriteQueryResults"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.lake.arn}/analytics/*"]
  }

  # Explicit, not merely absent. An absent allow is reversed by any later
  # policy that grants more; this is not.
  statement {
    sid     = "NeverRaw"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      "${aws_s3_bucket.lake.arn}/raw/*",
    ]
  }
}

resource "aws_iam_role" "analyst" {
  name                 = "lab-data-analyst"
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  permissions_boundary = aws_iam_policy.boundary.arn
}

resource "aws_iam_role_policy" "analyst" {
  name   = "zone-access"
  role   = aws_iam_role.analyst.id
  policy = data.aws_iam_policy_document.analyst.json
}

# ---------------------------------------------------------------------------
# An independent opinion on whether anything is reachable from outside.
# ---------------------------------------------------------------------------
resource "aws_accessanalyzer_analyzer" "lab" {
  analyzer_name = "lab-data-access"
  type          = "ACCOUNT"
}
