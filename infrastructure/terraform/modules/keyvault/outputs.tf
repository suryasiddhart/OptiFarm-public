# Keyvault Module — Outputs

output "key_vault_id" {
  description = "Resource ID of the Azure Key Vault"
  value       = azurerm_key_vault.kv.id
}

output "key_vault_name" {
  description = "Name of the Azure Key Vault"
  value       = azurerm_key_vault.kv.name
}

output "key_vault_uri" {
  description = "URI of the Azure Key Vault"
  value       = azurerm_key_vault.kv.vault_uri
}
output "app_secret_names" {
  description = "Names of the application secrets stored in the Key Vault"
  value       = keys(azurerm_key_vault_secret.app)
}
