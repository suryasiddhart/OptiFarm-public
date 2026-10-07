# ACR Module — Azure Container Registry
#
# Provisions a single Azure Container Registry with admin access enabled.

resource "azurerm_container_registry" "acr" {
  name                = "acr${var.project_name}"
  resource_group_name = var.resource_grp
  location            = var.location
  sku                 = var.acr_sku
  admin_enabled       = true
  tags                = var.tags
}