# FarmApp — Unified Terraform Providers Configuration
#
# Consolidated providers for all infrastructure modules:
#   - ACR (Azure Container Registry)
#   - AKS (Azure Kubernetes Service)
#   - Key Vault
#   - VM (Virtual Machine)

terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "remote" {
    organization = "suryasiddhart-study"

    workspaces {
      name = "terraform-space"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azuread" {
  # Uses Azure CLI or environment variables for authentication
}