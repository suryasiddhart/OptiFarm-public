# Keyvault Module — Azure Key Vault
#
# Provisions an Azure Key Vault with RBAC authorization and public access.
# Grants the deploying user (object_id) the Key Vault Administrator role.

data "azurerm_resource_group" "rg" {
  name = var.resource_grp
}

resource "azurerm_key_vault" "kv" {
  name                       = var.key_vault_name
  location                   = var.location
  resource_group_name        = data.azurerm_resource_group.rg.name
  tenant_id                  = var.tenant_id
  sku_name                   = var.kv_sku_name
  soft_delete_retention_days = var.kv_soft_delete_retention_days
  purge_protection_enabled   = var.kv_purge_protection_enabled

  # RBAC authorization — no access policies needed
  enable_rbac_authorization = true

  # Public network access
  public_network_access_enabled = true

  tags = var.tags
}

# Grant the deploying user Key Vault Administrator role
resource "azurerm_role_assignment" "kv_admin" {
  scope                            = azurerm_key_vault.kv.id
  role_definition_name             = "Key Vault Administrator"
  principal_id                     = var.object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
# ─────────────────────────────────────────────
# Application Secrets (per environment)
# ─────────────────────────────────────────────
# Generated once and stored in Key Vault; synced into the k3s cluster by
# External Secrets Operator (ClusterSecretStore "azure-keyvault").
# Names follow the existing "<name>-<env>" convention (e.g. kubeconfig-dev).
# Passwords are alphanumeric so they can be embedded in DATABASE_URL as-is.
resource "random_password" "postgres" {
  for_each = toset(var.app_environments)
  length   = 32
  special  = false
}

resource "random_password" "jwt_secret_key" {
  for_each = toset(var.app_environments)
  length   = 64
  special  = false
}

locals {
  app_secrets = merge([
    for env in var.app_environments : {
      "postgres-user-${env}"     = var.app_db_username
      "postgres-password-${env}" = random_password.postgres[env].result
      "jwt-secret-key-${env}"    = random_password.jwt_secret_key[env].result
    }
  ]...)
}

resource "azurerm_key_vault_secret" "app" {
  for_each     = nonsensitive(toset(keys(local.app_secrets)))
  name         = each.key
  value        = local.app_secrets[each.key]
  key_vault_id = azurerm_key_vault.kv.id
  content_type = "text/plain"
  tags         = var.tags

  # Writing secrets needs the data-plane role granted above
  depends_on = [azurerm_role_assignment.kv_admin]

  # Allow rotation directly in Key Vault without Terraform reverting it
  lifecycle {
    ignore_changes = [value]
  }
}
