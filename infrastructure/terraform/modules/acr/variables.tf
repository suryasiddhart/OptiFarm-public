# ACR Module — Variables

variable "project_name" {
  description = "Project name used for ACR resource naming"
  type        = string
}

variable "resource_grp" {
  description = "Azure resource group name"
  type        = string
}

variable "location" {
  description = "Azure region for the ACR"
  type        = string
}

variable "acr_sku" {
  description = "SKU for the Azure Container Registry"
  type        = string
  default     = "Standard"
}

variable "tags" {
  description = "Tags applied to the ACR resource"
  type        = map(string)
  default     = {}
}