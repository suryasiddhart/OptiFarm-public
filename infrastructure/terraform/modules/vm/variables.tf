# VM Module — Variables

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
}

variable "admin_username" {
  description = "Admin username for SSH access"
  type        = string
  default     = "azureuser"
}

variable "ssh_key_name" {
  description = "Name of the SSH public key resource in Azure"
  type        = string
  default     = "optifarm-ssh-key"
}

# ─────────────────────────────────────────────
# Networking Variables
# ─────────────────────────────────────────────
variable "vnet_name" {
  description = "Name of the virtual network"
  type        = string
  default     = "optifarm-vnet"
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
  default     = "optifarm-subnet"
}

variable "subnet_address_prefixes" {
  description = "Address prefixes for the subnet"
  type        = list(string)
  default     = ["10.0.1.0/24"]
}

variable "public_ip_name" {
  description = "Name of the public IP address"
  type        = string
  default     = "optifarm-pip"
}

# ─────────────────────────────────────────────
# OS Disk Variables
# ─────────────────────────────────────────────
variable "os_disk_caching" {
  description = "Caching type for the OS disk"
  type        = string
  default     = "ReadWrite"
}

variable "os_disk_type" {
  description = "Storage account type for the OS disk"
  type        = string
  default     = "Standard_LRS"
}

# ─────────────────────────────────────────────
# Source Image Variables
# ─────────────────────────────────────────────
variable "source_image_publisher" {
  description = "Publisher of the source image"
  type        = string
  default     = "Canonical"
}

variable "source_image_offer" {
  description = "Offer of the source image"
  type        = string
  default     = "ubuntu-24_04-lts" # was "0001-com-ubuntu-server-jammy"
}

variable "source_image_sku" {
  description = "SKU of the source image"
  type        = string
  default     = "server" # was "24_04-lts-gen2"
}


variable "source_image_version" {
  description = "Version of the source image"
  type        = string
  default     = "latest"
}

# ─────────────────────────────────────────────
# Spot Instance Variables
# ─────────────────────────────────────────────
variable "spot_eviction_policy" {
  description = "Eviction policy for the spot VM"
  type        = string
  default     = "Deallocate"
}

variable "spot_max_price" {
  description = "Maximum bid price for the spot VM"
  type        = number
  default     = 0.05
}

# ─────────────────────────────────────────────
# Auto-shutdown Variables
# ─────────────────────────────────────────────
variable "auto_shutdown_time" {
  description = "Daily auto-shutdown time (HHmm)"
  type        = string
  default     = "2200"
}

variable "auto_shutdown_timezone" {
  description = "Timezone for auto-shutdown schedule"
  type        = string
  default     = "India Standard Time"
}