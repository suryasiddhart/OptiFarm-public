# Implementation Plan

[Overview]
Combine all 4 Terraform resources (ACR, AKS, Keyvault, VM) into a single unified directory `FarmApp/terraform/infra/` that shares one Terraform workspace, with each resource deployed conditionally via flag variables and structured as reusable modules.

This implementation consolidates the existing standalone Terraform configurations (`ACR/`, `AKS/`, `Keyvault/`, `VM/`) into a single root configuration with child modules under `modules/`. Each module is toggled on/off via boolean flag variables (`enable_acr`, `enable_aks`, `enable_keyvault`, `enable_vm`), allowing selective deployment from one shared state. Cross-module dependencies (e.g., AKS needs ACR ID for AcrPull role assignment, AKS needs Key Vault ID for KV Secrets User role) are handled at the root level by passing outputs between modules conditionally. The ACR duplication currently inside the AKS `main.tf` is removed — ACR becomes its own module and the AKS module receives the ACR resource ID as an input variable. The old directories are kept intact for reference.

[Types]
No type system changes — this is a Terraform HCL infrastructure project.

Key variable definitions across the root and modules:

**Root-level flag variables (`infra/variables.tf`):**
- `enable_acr` — bool, default `false` — Whether to deploy the ACR module
- `enable_aks` — bool, default `false` — Whether to deploy the AKS module
- `enable_keyvault` — bool, default `false` — Whether to deploy the Key Vault module
- `enable_vm` — bool, default `false` — Whether to deploy the VM module

**Root-level shared variables (`infra/variables.tf`):**
- `environment` — string, default `dev`
- `location` — string, default `Central India`
- `project_name` — string, default `optifarm`
- `resource_grp` — string, default `Optifarm-dev`
- `tags` — map(string), default `{ Project = "optifarm", ManagedBy = "Terraform", Environment = "dev" }`

**Module-specific variables** — see each module's `variables.tf` for full details. Each module accepts the shared variables plus its own resource-specific variables with defaults carried over from the original configurations.

[Files]
Single sentence describing file modifications: Create a new `infra/` directory with root-level configuration files and 4 child module directories, each containing `main.tf`, `variables.tf`, and `outputs.tf`.

**New files to be created:**

Root level:
- `FarmApp/terraform/infra/providers.tf` — Terraform provider configuration (azurerm ~> 3.100, azuread ~> 2.50, random ~> 3.6, tls ~> 4.0), backend "remote" block pointing to TFC workspace `terraform-space`, azurerm provider features with key_vault block
- `FarmApp/terraform/infra/variables.tf` — All root-level variables: shared variables + 4 flag variables + all resource-specific variables (consolidated from the 4 old variables.tf files)
- `FarmApp/terraform/infra/main.tf` — Root orchestration: data sources, module blocks for acr/aks/keyvault/vm with `count` conditionals, cross-module wiring
- `FarmApp/terraform/infra/outputs.tf` — Consolidated outputs from all 4 modules (conditional references using `try()` or `one()`)
- `FarmApp/terraform/infra/README.md` — Usage documentation

ACR module:
- `FarmApp/terraform/infra/modules/acr/main.tf` — `azurerm_container_registry` resource (from ACR/main.tf)
- `FarmApp/terraform/infra/modules/acr/variables.tf` — ACR-specific variables (project_name, resource_grp, location, acr_sku, tags)
- `FarmApp/terraform/infra/modules/acr/outputs.tf` — acr_id, acr_login_server, acr_admin_username, acr_admin_password

AKS module:
- `FarmApp/terraform/infra/modules/aks/main.tf` — `azurerm_kubernetes_cluster` + role assignments (AcrPull using input acr_id, KV Secrets User using input key_vault_id). ACR resource removed. Key Vault data sources removed (replaced by input variables). random_string for suffix retained.
- `FarmApp/terraform/infra/modules/aks/variables.tf` — AKS-specific variables + `acr_id` (input), `key_vault_id` (input), `key_vault_name` (input)
- `FarmApp/terraform/infra/modules/aks/outputs.tf` — aks_cluster_name, aks_kube_config, aks_managed_identity_client_id

Keyvault module:
- `FarmApp/terraform/infra/modules/keyvault/main.tf` — `azurerm_key_vault` + `azurerm_role_assignment` for Key Vault Administrator (from Keyvault/main.tf)
- `FarmApp/terraform/infra/modules/keyvault/variables.tf` — Keyvault-specific variables (key_vault_name, kv_sku_name, kv_soft_delete_retention_days, kv_purge_protection_enabled, resource_grp, location, tags)
- `FarmApp/terraform/infra/modules/keyvault/outputs.tf` — key_vault_id, key_vault_name, key_vault_uri

VM module:
- `FarmApp/terraform/infra/modules/vm/main.tf` — All VM resources (tls_private_key, azurerm_ssh_public_key, vnet, subnet, nsg, public_ip, nic, nsg association, linux_virtual_machine, auto_shutdown) (from VM/main.tf)
- `FarmApp/terraform/infra/modules/vm/variables.tf` — VM-specific variables (vm_name, vm_size, admin_username, ssh_key_name, image refs, networking, disk, spot, auto-shutdown, resource_grp, location, tags)
- `FarmApp/terraform/infra/modules/vm/outputs.tf` — vm_name, vm_public_ip_address, vm_private_ip_address, vm_admin_username, vm_ssh_private_key, vm_ssh_public_key_name, vm_managed_identity_principal_id, vm_id, vnet_id, subnet_id, ssh_connect_command

**Existing files NOT modified** (old directories kept for reference):
- `FarmApp/terraform/ACR/*` — unchanged
- `FarmApp/terraform/AKS/*` — unchanged
- `FarmApp/terraform/Keyvault/*` — unchanged
- `FarmApp/terraform/VM/*` — unchanged

[Functions]
No function modifications — Terraform HCL has no functions in the traditional sense.

Key Terraform constructs used:
- `count = var.enable_xxx ? 1 : 0` — conditional module instantiation at root level
- `module "acr"` block with `source = "./modules/acr"`
- `module "aks"` block with `source = "./modules/aks"`, passing `acr_id = module.acr[0].acr_id` and `key_vault_id = module.keyvault[0].key_vault_id`
- `try(module.acr[0].acr_id, null)` pattern in outputs for conditional references
- `data "azurerm_client_config" "current"` at root level, passed to modules that need it

[Classes]
No class modifications — Terraform HCL has no classes.

[Dependencies]
No new external dependencies. All providers already used in existing modules:
- `azurerm` ~> 3.100 (existing)
- `azuread` ~> 2.50 (existing)
- `random` ~> 3.6 (existing)
- `tls` ~> 4.0 (existing, from VM module)

Integration: The root `providers.tf` consolidates all 4 providers into a single required_providers block. The backend "remote" block is included at the root level only (not in child modules).

[Testing]
Validation strategy:
1. Run `terraform fmt -recursive` in `infra/` directory to ensure formatting
2. Run `terraform init` in `infra/` to initialize providers and download modules
3. Run `terraform validate` to check configuration syntax
4. Run `terraform plan` with various flag combinations (e.g., `-var="enable_acr=true"`) to verify conditional deployment works
5. Verify that cross-module references resolve correctly when multiple modules are enabled

No automated test files — Terraform validation is manual via plan/apply.

[Implementation Order]
1. Create `FarmApp/terraform/infra/providers.tf` with consolidated providers and backend
2. Create `FarmApp/terraform/infra/modules/acr/` — `main.tf`, `variables.tf`, `outputs.tf` (extracted from ACR/)
3. Create `FarmApp/terraform/infra/modules/keyvault/` — `main.tf`, `variables.tf`, `outputs.tf` (extracted from Keyvault/)
4. Create `FarmApp/terraform/infra/modules/vm/` — `main.tf`, `variables.tf`, `outputs.tf` (extracted from VM/)
5. Create `FarmApp/terraform/infra/modules/aks/` — `main.tf`, `variables.tf`, `outputs.tf` (extracted from AKS/, ACR resource removed, acr_id/key_vault_id added as inputs)
6. Create `FarmApp/terraform/infra/variables.tf` — all shared + flag + resource-specific variables
7. Create `FarmApp/terraform/infra/main.tf` — root orchestration with conditional module blocks and cross-module wiring
8. Create `FarmApp/terraform/infra/outputs.tf` — consolidated conditional outputs
9. Create `FarmApp/terraform/infra/README.md` — usage documentation
10. Run `terraform fmt -recursive`, `terraform init`, `terraform validate` in `infra/` directory