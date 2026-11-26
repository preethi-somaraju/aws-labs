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
      Lab       = "03-s3-data-lake"
      ManagedBy = "terraform"
    }
  }
}

# A random suffix rather than the account ID: bucket names reach plan output,
# CLI logs and screenshots, and the account ID would go with them.
resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  bucket = "lab-lake-${random_id.suffix.hex}"
  zones  = ["raw/", "curated/", "analytics/"]

  # Every path a PutObject is allowed to land on. Anything else is denied by
  # the bucket policy, so the layout cannot drift.
  zone_arns = flatten([
    for z in local.zones : [
      "${aws_s3_bucket.lake.arn}/${z}",
      "${aws_s3_bucket.lake.arn}/${z}*",
    ]
  ])
}

resource "aws_s3_bucket" "lake" {
  bucket        = local.bucket
  force_destroy = true # teardown must not need manual emptying
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# A bad pipeline run overwriting curated data is the failure versioning exists
# for. It also means noncurrent versions bill until a lifecycle rule removes
# them, which is why the rules below are not optional.
resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = true
  }
}

# S3 has no directories. A zero-byte key per zone makes the layout visible in
# the console and gives the tests something to list against.
resource "aws_s3_object" "zone" {
  for_each = toset(local.zones)
  bucket   = aws_s3_bucket.lake.id
  key      = each.value
  content  = ""
}

# ---------------------------------------------------------------------------
# Bucket policy. Lab 02 enforced the zones through identity policy — who may
# touch which prefix. These apply to every caller, including the account root.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "lake" {
  statement {
    sid    = "DenyNonTLS"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.lake.arn, "${aws_s3_bucket.lake.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  # A naming convention nothing checks becomes eleven top-level prefixes
  # inside a year.
  statement {
    sid    = "DenyWritesOutsideZones"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions       = ["s3:PutObject"]
    not_resources = local.zone_arns
  }

  # Enforces the algorithm, not the presence of a header. Both conditions are
  # required: StringNotEquals on an absent key evaluates true, so without the
  # Null test this statement would also deny every caller that simply did not
  # send the header — which is the bug in the version below it.
  statement {
    sid    = "DenyWrongSSEAlgorithm"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.lake.arn}/*"]
    condition {
      test     = "Null"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["false"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["AES256"]
    }
  }

  # The copy-pasted classic. Off by default; test 3 turns it on to record what
  # it actually does now that S3 encrypts everything regardless.
  dynamic "statement" {
    for_each = var.legacy_sse_deny ? [1] : []
    content {
      sid    = "DenyMissingSSEHeader"
      effect = "Deny"
      principals {
        type        = "*"
        identifiers = ["*"]
      }
      actions   = ["s3:PutObject"]
      resources = ["${aws_s3_bucket.lake.arn}/*"]
      condition {
        test     = "Null"
        variable = "s3:x-amz-server-side-encryption"
        values   = ["true"]
      }
    }
  }
}

resource "aws_s3_bucket_policy" "lake" {
  bucket = aws_s3_bucket.lake.id
  policy = data.aws_iam_policy_document.lake.json

  # Block Public Access evaluates the policy on write; the deny-only policy is
  # not public, but the settings must exist first either way.
  depends_on = [aws_s3_bucket_public_access_block.lake]
}

# ---------------------------------------------------------------------------
# Lifecycle. The rules that make a lake affordable are the same rules that can
# make it unreadable, so each zone gets the one its contents justify.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_lifecycle_configuration" "lake" {
  bucket     = aws_s3_bucket.lake.id
  depends_on = [aws_s3_bucket_versioning.lake]

  # Immutable landing data: read heavily for a month, then kept for
  # reprocessing. GLACIER_IR and not DEEP_ARCHIVE because a reader must still
  # be able to read it without a restore.
  rule {
    id     = "raw-cooling"
    status = "Enabled"
    filter { prefix = "raw/" }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    noncurrent_version_expiration { noncurrent_days = 30 }
  }

  # Current version stays hot. History is for recovery, not for ever.
  rule {
    id     = "curated-history"
    status = "Enabled"
    filter { prefix = "curated/" }

    noncurrent_version_expiration { noncurrent_days = 90 }
  }

  # Query results are derived and reproducible.
  rule {
    id     = "analytics-disposable"
    status = "Enabled"
    filter { prefix = "analytics/" }

    expiration { days = 30 }
    noncurrent_version_expiration { noncurrent_days = 1 }
  }

  # Parts of an upload that never completed bill as storage and do not appear
  # in a listing. Nothing else in S3 is invisible and billed.
  rule {
    id     = "abort-orphaned-parts"
    status = "Enabled"
    filter {}

    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}
