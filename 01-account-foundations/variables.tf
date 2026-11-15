variable "region" {
  description = "AWS region for all labs"
  type        = string
  default     = "us-east-1"
}

variable "profile" {
  description = "Local AWS CLI profile"
  type        = string
  default     = "preethi-portfolio"
}

variable "alert_email" {
  description = "Where budget alerts go"
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly spend ceiling before alerts fire"
  type        = string
  default     = "5"
}
