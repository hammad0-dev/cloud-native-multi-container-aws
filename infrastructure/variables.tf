variable "region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
  validation {
    condition     = can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]+$", var.region))
    error_message = "Supply an AWS region name such as us-east-1."
  }
}
variable "project" {
  description = "Short lowercase resource prefix"
  type        = string
  default     = "document-vault"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,25}$", var.project))
    error_message = "Use 3-26 lowercase letters, digits and hyphens."
  }
}
variable "http_cidr" {
  description = "Trusted browser IPv4 CIDR; HTTP demo uses dummy data only"
  type        = string
  validation {
    condition     = can(cidrnetmask(var.http_cidr)) && var.http_cidr != "0.0.0.0/0"
    error_message = "Supply a restricted trusted IPv4 CIDR."
  }
}
variable "instance_type" {
  description = "EC2 x86 instance size"
  type        = string
  default     = "t3.small"
}
variable "db_instance_class" {
  description = "Single-AZ learning RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}
variable "final_snapshot_identifier" {
  description = "Unique RDS final snapshot name; change before subsequent teardown"
  type        = string
  default     = "document-vault-final"
}
variable "deletion_protection" {
  description = "Disable deliberately before an authorized teardown"
  type        = bool
  default     = true
}
