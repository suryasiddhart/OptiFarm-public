# AKS Module — Azure Kubernetes Service
#
# Provisions an AKS cluster with:
#   - System node pool
#   - User node pool (auto-scaling)
#   - Managed identity (SystemAssigned)
#   - RBAC enabled
#   - Network plugin (azure)
#   - ACR attachment (via acr_id input)
#   - Key Vault secrets provider

# ─────────────────────────────────────────────
# Data Sources
# ─────────────────────────────────────────────
data "azurerm_resource_group" "rg" {
  name = var.resource_grp
}

data "azurerm_client_config" "current" {}

# ─────────────────────────────────────────────
# AKS Cluster
# ─────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_name
  location            = var.location
  resource_group_name = var.resource_grp
  dns_prefix          = var.aks_dns_prefix
  kubernetes_version  = var.kubernetes_version
  tags                = var.tags

  # System-assigned managed identity
  identity {
    type = "SystemAssigned"
  }

  # Enable RBAC
  role_based_access_control_enabled = true

  # Default (system) node pool
  default_node_pool {
    name           = "systempool"
    node_count     = var.system_node_count
    vm_size        = var.system_node_vm_size
    os_sku         = "Ubuntu"
    vnet_subnet_id = var.aks_subnet_id
    type           = "VirtualMachineScaleSets"
    node_labels    = { "pool" = "system" }
  }

  # Network profile
  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = var.service_cidr
    dns_service_ip    = var.dns_service_ip
  }

  # Key Vault secrets provider
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }
}

# ─────────────────────────────────────────────
# User Node Pool (auto-scaling)
# ─────────────────────────────────────────────
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "userpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = var.user_node_vm_size
  os_sku                = "Ubuntu"
  vnet_subnet_id        = var.aks_subnet_id
  node_labels           = { "pool" = "user" }

  enable_auto_scaling = true
  min_count           = var.user_node_min_count
  max_count           = var.user_node_max_count
}

# ─────────────────────────────────────────────
# ACR Pull role assignment
# ─────────────────────────────────────────────
resource "azurerm_role_assignment" "aks_acr_pull" {
  count                            = var.acr_id != null ? 1 : 0
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}