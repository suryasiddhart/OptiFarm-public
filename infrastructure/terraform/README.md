# FarmApp Infrastructure — Terraform

Consolidated, modular Terraform configuration for provisioning Azure infrastructure: ACR, Key Vault, VM, and AKS.

## Structure

```
infra/
├── main.tf          # Root orchestration with conditional modules
├── variables.tf     # Shared + flag + resource-specific variables
├── outputs.tf       # Consolidated conditional outputs
├── providers.tf     # Provider configuration & backend
├── README.md        # This file
└── modules/
    ├── acr/         # Azure Container Registry
    ├── keyvault/    # Azure Key Vault (RBAC, public access)
    ├── vm/          # Linux VM with SSH key + managed identity
    └── aks/         # AKS cluster with system + user node pools
```

## Usage

### 1. Initialize

```bash
cd FarmApp/terraform/infra
terraform init
```

### 2. Create a `terraform.tfvars` file

```hcl
resource_grp = "your-resource-group-name"
location     = "centralindia"

# Feature flags — toggle modules on/off
create_acr       = true
create_keyvault  = true
create_vm        = true
create_aks       = true

# Key Vault
key_vault_name = "optifarm-kv1"

# ACR
acr_sku = "Standard"
```

### 3. Plan & Apply

```bash
terraform plan
terraform apply
```

## Key Vault Details

The Key Vault (`optifarm-kv1`) is provisioned with:
- **Location:** Central India
- **Public network access:** Enabled
- **RBAC:** Enabled (Azure RBAC for data plane authorization)
- **Purge protection:** Enabled
- **Soft delete:** 7-day retention

## Cross-Module Wiring

- **ACR → AKS:** When both modules are enabled, the AKS kubelet identity is granted `AcrPull` on the ACR automatically.
- **AKS VNet/Subnet:** Created at the root level and passed to the AKS module.

## Feature Flags

Each module can be independently toggled:

| Flag | Default | Description |
|------|---------|-------------|
| `create_acr` | `true` | Provision Azure Container Registry |
| `create_keyvault` | `true` | Provision Azure Key Vault |
| `create_vm` | `true` | Provision Linux VM |
| `create_aks` | `true` | Provision AKS cluster + VNet/Subnet |