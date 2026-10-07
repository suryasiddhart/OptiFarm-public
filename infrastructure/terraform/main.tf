# FarmApp Infra — Root Orchestration
#
# Conditionally provisions ACR, Key Vault, VM, and AKS modules.
# Cross-module wiring:
#   - ACR id → AKS (AcrPull role assignment)
#   - VM workload UAMI → Key Vault (Key Vault Secrets User, for ESO)
#   - VM workload UAMI → ACR (AcrPull, for ESO-generated pull secrets)
#   - AKS VNet & Subnet (root-level) → AKS module

# ─────────────────────────────────────────────
# Data Sources — current client config for tenant/object IDs
# ─────────────────────────────────────────────
data "azurerm_client_config" "current" {}

# ─────────────────────────────────────────────
# ACR Module (conditional)
# ─────────────────────────────────────────────
module "acr" {
  count  = var.create_acr ? 1 : 0
  source = "./modules/acr"

  project_name = var.project_name
  resource_grp = var.resource_grp
  location     = var.location
  acr_sku      = var.acr_sku
  tags         = var.tags
}

# ─────────────────────────────────────────────
# Key Vault Module (conditional)
# ─────────────────────────────────────────────
module "keyvault" {
  count  = var.create_keyvault ? 1 : 0
  source = "./modules/keyvault"

  key_vault_name                = var.key_vault_name
  resource_grp                  = var.resource_grp
  location                      = var.location
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  object_id                     = data.azurerm_client_config.current.object_id
  kv_sku_name                   = var.kv_sku_name
  kv_soft_delete_retention_days = var.kv_soft_delete_retention_days
  kv_purge_protection_enabled   = var.kv_purge_protection_enabled
  app_environments              = var.app_environments
  app_db_username               = var.app_db_username
  tags                          = var.tags
}

# ─────────────────────────────────────────────
# VM Module (conditional)
# ─────────────────────────────────────────────
module "vm" {
  count          = var.create_vm ? 1 : 0
  source         = "./modules/vm"
  resource_grp   = var.resource_grp
  location       = var.vm_location
  tags           = var.tags
  vm_name        = var.vm_name
  vm_size        = var.vm_size
  admin_username = var.admin_username
}

# ─────────────────────────────────────────────
# VM Workload Identity (UAMI) → Key Vault + ACR
# ─────────────────────────────────────────────
# External Secrets Operator on the k3s VM authenticates with the VM's
# user-assigned workload identity (IMDS), so no credentials are stored in
# the cluster. It reads app secrets from Key Vault and mints ACR pull tokens.
resource "azurerm_role_assignment" "uami_kv_secrets_user" {
  count                            = var.create_vm && var.create_keyvault ? 1 : 0
  scope                            = module.keyvault[0].key_vault_id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = module.vm[0].workload_identity_principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "uami_acr_pull" {
  count                            = var.create_vm && var.create_acr ? 1 : 0
  scope                            = module.acr[0].acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = module.vm[0].workload_identity_principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

# ─────────────────────────────────────────────
# AKS VNet & Subnet (root-level, only if AKS is created)
# ─────────────────────────────────────────────
resource "azurerm_virtual_network" "aks_vnet" {
  count               = var.create_aks ? 1 : 0
  name                = "${var.aks_name}-vnet"
  location            = var.location
  resource_group_name = var.resource_grp
  address_space       = var.aks_vnet_address_space
  tags                = var.tags
}

resource "azurerm_subnet" "aks_subnet" {
  count                = var.create_aks ? 1 : 0
  name                 = "${var.aks_name}-subnet"
  resource_group_name  = var.resource_grp
  virtual_network_name = azurerm_virtual_network.aks_vnet[0].name
  address_prefixes     = var.aks_subnet_address_prefixes
}

# ─────────────────────────────────────────────
# AKS Module (conditional)
# ─────────────────────────────────────────────
module "aks" {
  count  = var.create_aks ? 1 : 0
  source = "./modules/aks"

  resource_grp       = var.resource_grp
  location           = var.location
  tags               = var.tags
  aks_name           = var.aks_name
  aks_dns_prefix     = var.aks_dns_prefix
  kubernetes_version = var.kubernetes_version
  aks_subnet_id      = azurerm_subnet.aks_subnet[0].id

  # Wire ACR id if ACR is created
  acr_id = var.create_acr ? module.acr[0].acr_id : null
}