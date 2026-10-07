# FarmApp Infra — Root Variables

# ─────────────────────────────────────────────
# Shared / Common Variables
# ─────────────────────────────────────────────
variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "optifarm"
}

variable "environment" {
  description = "Environment name (e.g. dev, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "centralindia"
}

variable "resource_grp" {
  description = "Azure resource group name (must already exist)"
  type        = string
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Project   = "optifarm"
    ManagedBy = "terraform"
  }
}

# ─────────────────────────────────────────────
# Feature Flags
# ─────────────────────────────────────────────
variable "create_acr" {
  description = "Whether to create the ACR module"
  type        = bool
  default     = true
}

variable "create_keyvault" {
  description = "Whether to create the Key Vault module"
  type        = bool
  default     = true
}

variable "create_vm" {
  description = "Whether to create the VM module"
  type        = bool
  default     = true
}

variable "create_aks" {
  description = "Whether to create the AKS module"
  type        = bool
  default     = false
}

# ─────────────────────────────────────────────
# ACR Variables
# ─────────────────────────────────────────────
variable "acr_sku" {
  description = "SKU for the Azure Container Registry"
  type        = string
  default     = "Standard"
}

# ─────────────────────────────────────────────
# Key Vault Variables
# ─────────────────────────────────────────────
variable "key_vault_name" {
  description = "Name of the Azure Key Vault"
  type        = string
  default     = "optifarm-kv1"
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

# ─────────────────────────────────────────────
# VM Variables
# ─────────────────────────────────────────────
variable "vm_name" {
  description = "Name of the virtual machine"
  type        = string
  default     = "optifarm-vm"
}

variable "vm_size" {
  description = "Size of the virtual machine"
  type        = string
  default     = "Standard_D4as_v5"
}

variable "admin_username" {
  description = "Admin username for SSH access"
  type        = string
  default     = "azureuser"
}

variable "vm_location" {
  description = "Location of the virtual machine"
  type        = string
  default     = "Central India"
}
# ─────────────────────────────────────────────
# AKS Variables
# ─────────────────────────────────────────────
variable "aks_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "aks-optifarm"
}

variable "aks_dns_prefix" {
  description = "DNS prefix for the AKS cluster"
  type        = string
  default     = "optifarm-aks"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the AKS cluster"
  type        = string
  default     = "1.29"
}

variable "aks_vnet_address_space" {
  description = "Address space for the AKS virtual network"
  type        = list(string)
  default     = ["10.2.0.0/16"]
}

variable "aks_subnet_address_prefixes" {
  description = "Address prefixes for the AKS subnet"
  type        = list(string)
  default     = ["10.2.1.0/24"]
}