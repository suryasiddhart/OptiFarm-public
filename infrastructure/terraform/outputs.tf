# FarmApp Infra — Consolidated Outputs

# ─────────────────────────────────────────────
# ACR Outputs
# ─────────────────────────────────────────────
output "acr_id" {
  description = "Resource ID of the ACR (if created)"
  value       = var.create_acr ? module.acr[0].acr_id : null
}

output "acr_login_server" {
  description = "ACR login server URL (if created)"
  value       = var.create_acr ? module.acr[0].acr_login_server : null
}

# ─────────────────────────────────────────────
# Key Vault Outputs
# ─────────────────────────────────────────────
output "key_vault_id" {
  description = "Resource ID of the Key Vault (if created)"
  value       = var.create_keyvault ? module.keyvault[0].key_vault_id : null
}

output "key_vault_name" {
  description = "Name of the Key Vault (if created)"
  value       = var.create_keyvault ? module.keyvault[0].key_vault_name : null
}

output "key_vault_uri" {
  description = "URI of the Key Vault (if created)"
  value       = var.create_keyvault ? module.keyvault[0].key_vault_uri : null
}

output "app_secret_names" {
  description = "Names of the application secrets stored in the Key Vault (if created)"
  value       = var.create_keyvault ? module.keyvault[0].app_secret_names : null
}

# ─────────────────────────────────────────────
# VM Outputs
# ─────────────────────────────────────────────
output "vm_id" {
  description = "Resource ID of the VM (if created)"
  value       = var.create_vm ? module.vm[0].vm_id : null
}

output "vm_public_ip" {
  description = "Public IP of the VM (if created)"
  value       = var.create_vm ? module.vm[0].vm_public_ip : null
}

output "vm_public_ip_fqdn" {
  description = "FQDN of the VM public IP (if created)"
  value       = var.create_vm ? module.vm[0].vm_public_ip_fqdn : null
}

output "workload_identity_client_id" {
  description = "Client ID of the VM workload UAMI used by ESO (if created)"
  value       = var.create_vm ? module.vm[0].workload_identity_client_id : null
}

output "tls_private_key" {
  description = "Private SSH key for the VM (for Ansible access)"
  value       = var.create_vm ? module.vm[0].tls_private_key : null
  sensitive   = true
}

# ─────────────────────────────────────────────
# AKS Outputs
# ─────────────────────────────────────────────
output "aks_id" {
  description = "Resource ID of the AKS cluster (if created)"
  value       = var.create_aks ? module.aks[0].aks_id : null
}

output "aks_name" {
  description = "Name of the AKS cluster (if created)"
  value       = var.create_aks ? module.aks[0].aks_name : null
}