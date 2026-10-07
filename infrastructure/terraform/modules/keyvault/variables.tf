# Keyvault Module — Variables

variable "key_vault_name" {
  description = "Name of the Azure Key Vault"
  type        = string
}

variable "resource_grp" {
  description = "Azure resource group name"
  type        = string
}

variable "location" {
  description = "Azure region for the Key Vault"
  type        = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID for the Key Vault"
  type        = string
}

variable "object_id" {
  description = "Object ID of the deploying user/principal to grant Key Vault Administrator"
  type        = string
}

variable "kv_sku_name" {
  description = "SKU name for the Key Vault"
  type        = string
  default     = "standard"
}

variable "kv_soft_delete_retention_days" {
  description = "Number of days soft-deleted secrets are retained"
  type        = number
  default     = 7
}

variable "kv_purge_protection_enabled" {
  description = "Whether purge protection is enabled on the Key Vault"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to the Key Vault resource"
  type        = map(string)
  default     = {}
}
variable "app_environments" {
  description = "Application environments to generate Key Vault secrets for"
  type        = list(string)
  default     = ["dev", "staging", "prod"]
}

variable "app_db_username" {
  description = "Postgres username stored in Key Vault for each environment"
  type        = string
  default     = "optifarm"
}
