# VM Module — Azure Linux Virtual Machine
#
# Provisions the full VM stack:
#   - SSH Key
#   - Virtual Network & Subnet
#   - Public IP
#   - Network Interface (NIC)
#   - Network Security Group (SSH inbound)
#   - Azure Linux Virtual Machine (Spot, Trusted Launch)
#   - System Assigned Managed Identity
#   - User Assigned Managed Identity (workload identity for ESO / ACR pulls)
#   - Auto-shutdown schedule

# ─────────────────────────────────────────────
# Data Sources
# ─────────────────────────────────────────────
data "azurerm_resource_group" "rg" {
  name = var.resource_grp
}

# ─────────────────────────────────────────────
# SSH Key
# ─────────────────────────────────────────────
resource "tls_private_key" "vm_ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "azurerm_ssh_public_key" "vm" {
  name                = var.ssh_key_name
  resource_group_name = var.resource_grp
  location            = var.location
  public_key          = tls_private_key.vm_ssh.public_key_openssh
  tags                = var.tags
}

# ─────────────────────────────────────────────
# User Assigned Managed Identity (workload identity)
# ─────────────────────────────────────────────
# Used by External Secrets Operator on k3s (via IMDS) to read Key Vault
# secrets and to mint ACR pull tokens. Role assignments live at the root.
resource "azurerm_user_assigned_identity" "workload" {
  name                = "${var.vm_name}-workload-id"
  location            = var.location
  resource_group_name = var.resource_grp
  tags                = var.tags
}

# ─────────────────────────────────────────────
# Virtual Network & Subnet
# ─────────────────────────────────────────────
resource "azurerm_virtual_network" "vnet" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_grp
  address_space       = var.vnet_address_space
  tags                = var.tags
}

resource "azurerm_subnet" "subnet" {
  name                 = var.subnet_name
  resource_group_name  = var.resource_grp
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = var.subnet_address_prefixes
}

# ─────────────────────────────────────────────
# Network Security Group (SSH inbound)
# ─────────────────────────────────────────────
resource "azurerm_network_security_group" "nsg" {
  name                = "${var.vm_name}-nsg"
  location            = var.location
  resource_group_name = var.resource_grp
  tags                = var.tags

  security_rule {
    name                       = "SSH"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # k3s API server
  security_rule {
    name                       = "K3sAPI"
    priority                   = 1010
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "6443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # HTTP ingress
  security_rule {
    name                       = "HTTP"
    priority                   = 1020
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # HTTPS ingress
  security_rule {
    name                       = "HTTPS"
    priority                   = 1030
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# ─────────────────────────────────────────────
# Public IP
# ─────────────────────────────────────────────
resource "azurerm_public_ip" "vm" {
  name                = var.public_ip_name
  location            = var.location
  resource_group_name = var.resource_grp
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = var.vm_name
  tags                = var.tags
}

# ─────────────────────────────────────────────
# Network Interface (NIC)
# ─────────────────────────────────────────────
resource "azurerm_network_interface" "vm" {
  name                = "${var.vm_name}-nic"
  location            = var.location
  resource_group_name = var.resource_grp
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm.id
  }
}

resource "azurerm_network_interface_security_group_association" "nsg" {
  network_interface_id      = azurerm_network_interface.vm.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# ─────────────────────────────────────────────
# Virtual Machine — Trusted Launch, Spot, Ubuntu 24.04 LTS
# ─────────────────────────────────────────────
resource "azurerm_linux_virtual_machine" "vm" {
  name                            = var.vm_name
  location                        = var.location
  resource_group_name             = var.resource_grp
  size                            = var.vm_size
  admin_username                  = var.admin_username
  network_interface_ids           = [azurerm_network_interface.vm.id]
  disable_password_authentication = true
  tags                            = var.tags

  # Trusted Launch
  secure_boot_enabled = true
  vtpm_enabled        = true

  # SSH Key
  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.vm_ssh.public_key_openssh
  }

  # OS Disk
  os_disk {
    name                 = "${var.vm_name}-osdisk"
    caching              = var.os_disk_caching
    storage_account_type = var.os_disk_type
  }

  # Source Image — Ubuntu Server 24.04 LTS Gen2
  source_image_reference {
    publisher = var.source_image_publisher
    offer     = var.source_image_offer
    sku       = var.source_image_sku
    version   = var.source_image_version
  }

  # Azure Spot Instance
  priority        = "Spot"
  eviction_policy = var.spot_eviction_policy
  max_bid_price   = var.spot_max_price

  # System + User Assigned Managed Identities
  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.workload.id]
  }

  # Availability Zone
  zone = "1"
}

# ─────────────────────────────────────────────
# Auto-shutdown Schedule
# ─────────────────────────────────────────────
resource "azurerm_dev_test_global_vm_shutdown_schedule" "auto_shutdown" {
  virtual_machine_id    = azurerm_linux_virtual_machine.vm.id
  location              = var.location
  enabled               = true
  daily_recurrence_time = var.auto_shutdown_time
  timezone              = var.auto_shutdown_timezone

  notification_settings {
    enabled = false
  }

  tags = var.tags
}