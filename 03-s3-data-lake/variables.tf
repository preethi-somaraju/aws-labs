variable "region" {
  type    = string
  default = "us-east-1"
}

variable "profile" {
  type    = string
  default = "preethi-labs"
}

# Applies the widely copied "deny uploads with no SSE header" statement, which
# this lab exists partly to discredit. Test 3 flips it on; the lab runs with it
# off.
variable "legacy_sse_deny" {
  type    = bool
  default = false
}
