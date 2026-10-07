# VM Module — Outputs

output "vm_id" {
  description = "Resource ID of the virtual machine"
  value       = azurerm_linux_virtual_machine.vm.id
}

output "vm_name" {
  description = "Name of the virtual machine"
  value       = azurerm_linux_virtual_machine.vm.name
}

output "vm_public_ip" {
  description = "Public IP address of the virtual machine"
  value       = azurerm_public_ip.vm.ip_address
}

output "vm_public_ip_fqdn" {
  description = "FQDN of the public IP"
  value       = azurerm_public_ip.vm.fqdn
}

output "vm_private_ip" {
  description = "Private IP address of the virtual machine"
  value       = azurerm_network_interface.vm.private_ip_address
}

output "vm_principal_id" {
  description = "Principal ID of the system-assigned managed identity"
  value       = azurerm_linux_virtual_machine.vm.identity[0].principal_id
}

output "workload_identity_principal_id" {
  description = "Principal ID of the user-assigned workload identity"
  value       = azurerm_user_assigned_identity.workload.principal_id
}

output "workload_identity_client_id" {
  description = "Client ID of the user-assigned workload identity (used by ESO)"
  value       = azurerm_user_assigned_identity.workload.client_id
}

output "tls_private_key" {
  description = "Private SSH key for the VM"
  value       = tls_private_key.vm_ssh.private_key_pem
  sensitive   = true
}