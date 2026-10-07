# AKS Module — Variables

# ─────────────────────────────────────────────
# Shared Variables
# ─────────────────────────────────────────────
variable "resource_grp" {
  description = "Azure resource group name"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}

# ─────────────────────────────────────────────
# AKS Cluster Variables
# ─────────────────────────────────────────────
variable "aks_name" {
  description = "Name of the AKS cluster"
  type        = string
}

variable "aks_dns_prefix" {
  description = "DNS prefix for the AKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for the AKS cluster"
  type        = string
  default     = "1.29"
}

# ─────────────────────────────────────────────
# System Node Pool Variables
# ─────────────────────────────────────────────
variable "system_node_count" {
  description = "Number of nodes in the system node pool"
  type        = number
  default     = 1
}

variable "system_node_vm_size" {
  description = "VM size for the system node pool"
  type        = string
  default     = "Standard_B2s"
}

# ─────────────────────────────────────────────
# User Node Pool Variables
# ─────────────────────────────────────────────
variable "user_node_vm_size" {
  description = "VM size for the user node pool"
  type        = string
  default     = "Standard_B2s"
}

variable "user_node_min_count" {
  description = "Minimum node count for the user node pool"
  type        = number
  default     = 1
}

variable "user_node_max_count" {
  description = "Maximum node count for the user node pool"
  type        = number
  default     = 3
}

# ─────────────────────────────────────────────
# Network Variables
# ─────────────────────────────────────────────
variable "aks_subnet_id" {
  description = "Subnet ID for AKS nodes"
  type        = string
}

variable "service_cidr" {
  description = "CIDR for Kubernetes services"
  type        = string
  default     = "10.1.0.0/16"
}

variable "dns_service_ip" {
  description = "DNS service IP address"
  type        = string
  default     = "10.1.0.10"
}

# ─────────────────────────────────────────────
# ACR Integration
# ─────────────────────────────────────────────
variable "acr_id" {
  description = "Resource ID of the ACR to grant AcrPull (null to skip)"
  type        = string
  default     = null
}