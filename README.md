# OptiFarm (FarmApp)

OptiFarm is a precision-irrigation platform. Farmers register their fields, attach soil-moisture sensors to them, and watch the moisture of every part of each field update live on a grid, so they can see which areas need water.

- **Fields as grids.** Each field is divided into cells based on its size and crop spacing: rows = length ÷ crop interval, columns = breadth ÷ crop interval. A 2 m × 2 m field with 0.1 m spacing is a 20 × 20 grid.
- **Devices.** Each field can have several devices. A device is registered in the app, gets a one-time passkey, and reports the moisture of the field's cells over MQTT.
- **Live View.** A heatmap of the field shows the latest moisture of every cell, refreshed every 15 seconds.

The repository contains both the application (a React frontend, a FastAPI backend, TimescaleDB, and an MQTT → Kafka ingestion pipeline for device data) and the platform that delivers it: **Terraform and Ansible infrastructure automation**, a **blocking PR build-validation pipeline** with layered security gates, and a **promotion-based CD pipeline** that deploys to Kubernetes with automated TLS, secretless credentials, and post-deploy smoke tests.

---

## Contents

- [Application architecture](#application-architecture)
- [Highlights](#highlights)
- [Delivery architecture](#delivery-architecture)
- [Repository layout](#repository-layout)
- [Tech stack](#tech-stack)
- [Infrastructure automation](#infrastructure-automation)
- [PR build validation](#pr-build-validation)
- [Continuous delivery](#continuous-delivery)
- [Secrets management](#secrets-management)
- [Database migrations](#database-migrations)
- [HTTPS](#https)
- [Field-device ingestion](#field-device-ingestion)
- [Azure DevOps setup](#azure-devops-setup)
- [Local development](#local-development)
- [Known limitations and roadmap](#known-limitations-and-roadmap)

---

## Application architecture

```
                 Browser                                        Field devices (sensors)
                    │ HTTPS 443                                        │ MQTT over TLS 8883
                    ▼                                                  │ user = device ID, password = passkey
            ┌──────────────┐                                           ▼
            │ ingress-nginx│                                   ┌──────────────┐   logins rebuilt from the
            └──┬────────┬──┘                                   │  Mosquitto   │◄─ devices table on start
       /       │        │ /api                                 │ (MQTT broker)│   (dynsec-sync)
               ▼        ▼                                      └──────┬───────┘
      ┌──────────┐  ┌───────────────┐  creates / rotates / disables   │ optifarm/v1/devices/<id>/telemetry
      │ frontend │  │  api          │──── device logins ─────────────►│
      │ React +  │  │  FastAPI      │                                 ▼
      │ nginx    │  │  JWT auth     │                          ┌──────────────┐
      └──────────┘  └──────┬────────┘                          │ mqtt-bridge  │
                           │ SQL                               └──────┬───────┘
                           ▼                                          ▼  key = device ID (keeps order)
                    ┌──────────────────┐                       ┌──────────────┐  telemetry.raw
                    │   TimescaleDB    │                       │ Kafka        │  telemetry.dlq (rejects)
                    │ users · fields · │                       └──────┬───────┘
                    │ devices ·        │                              ▼
                    │ moisturedata     │◄──────────────────────┌──────────────────┐
                    └──────────────────┘   batch upserts       │ ingest-consumer  │
                                                               └──────────────────┘
```

| Component | Role |
|---|---|
| **frontend** (`farmapp-frontend/`) | React + Ant Design, served by nginx. My Fields list, a devices popup per field (add, rotate passkey, delete), and the Live View heatmap popup. Calls the API on the same host under `/api`. |
| **api** (`api/`) | FastAPI. User registration and JWT login, fields, devices, and moisture queries. When a device is created, rotated or deleted, it updates that device's broker login immediately. |
| **TimescaleDB** | PostgreSQL with TimescaleDB. Holds users, fields, devices (with a hash of each device's passkey) and `moisturedata`, a hypertable with one row per device per time. |
| **Mosquitto** | MQTT broker for devices. Each device can only publish to its own topic. Logins are rebuilt from the `devices` table every time the broker starts. |
| **mqtt-bridge** (`ingest/bridge.py`) | Forwards device messages to Kafka, keyed by device ID. It acknowledges a message to the broker only after Kafka has stored it, so nothing is lost if it restarts. |
| **Kafka** | Durable buffer between devices and the database. `telemetry.raw` holds incoming data (7 days); `telemetry.dlq` holds rejected messages with the reason. |
| **ingest-consumer** (`ingest/consumer.py`) | Validates messages, checks the cells against the device's field grid, and writes them to `moisturedata`. Duplicates are merged, and invalid messages go to the DLQ. |
| **simulator** (`simulator/`, optional) | Simulated devices that publish realistic moisture grids. Deployed only on request. |

**Main flows**
1. **Register a field:** the user enters its size and crop interval, which fixes its grid (rows × columns).
2. **Add a device:** the user names it in the field's devices popup. The API stores the device with a hash of a newly generated passkey, creates its broker login, and shows the device ID and passkey **once**.
3. **Report moisture:** the device publishes `{"ts": "...", "readings": {"moisture": {"m1_1": 31.4, "m2_5": 28.9}}}`, where `m<row>_<col>` names a grid cell (1-based). The reading flows broker → bridge → Kafka → consumer → `moisturedata`. A large grid can be sent in parts that share a timestamp.
4. **View:** Live View loads the field's readings and places each value in its cell, so `m2_5` appears at row 2, column 5. Each cell shows its newest value.

Details of the message format, validation and ordering are in [Field-device ingestion](#field-device-ingestion). Each environment (dev, staging, prod) runs this whole stack in its own Kubernetes namespace; the device-ingestion part is switched on per environment.

---

## Highlights

- **Infrastructure as code, end to end.** Modular, feature-flagged Terraform provisions ACR, Key Vault, a k3s host VM, and an optional AKS cluster. Ansible then bootstraps the cluster platform (k3s, ingress-nginx, cert-manager, External Secrets Operator). Both run from one pipeline with a reviewed plan and approval-gated applies.
- **No long-lived cloud credentials.** The pipeline authenticates to Azure with Workload Identity Federation (OIDC). In the cluster, External Secrets Operator reads Key Vault and mints short-lived ACR pull tokens through a managed identity. No secret is stored in the repo, the pipeline, or the cluster manifests.
- **Every PR is gated by 5 parallel blocking stages:** unit and integration tests against an ephemeral TimescaleDB, an Alembic migration round-trip, frontend lint/type/test/build, image builds, Helm and manifest checks, and five security scanners (Bandit, Semgrep, Gitleaks, Trivy image, Trivy dependency and IaC).
- **Promotion-based delivery.** `develop` deploys to dev, `main` to staging, and a `v*` tag to prod. Each deploy runs migrations safely, issues a Let's Encrypt certificate, and finishes with smoke tests.
- **Cost-aware by design.** The cluster host is an Azure Spot VM with nightly auto-shutdown, and every Terraform module can be toggled off with a flag.

---

## Delivery architecture

How code gets from a pull request to the running environments:

```
                         ┌──────────────────────── Azure DevOps ────────────────────────┐
                         │                                                              │
   Pull request ───────► │  pr-validation.yml        (Build Validation branch policy)   │
                         │  tests · migrations · scans · helm lint     → blocks merge   │
                         │                                                              │
   infra/* change ─────► │  infrastructure/azure-pipelines.yml                          │
                         │  validate → plan → apply (per env) → Ansible k3s bootstrap   │
                         │                                                              │
   app change ─────────► │  pipelines/azure-pipelines.yml                               │
                         │  build & push images → Helm deploy dev → staging → prod      │
                         └────────────┬───────────────────────────────┬─────────────────┘
                                      │ Workload Identity (OIDC)      │ kubeconfig from Key Vault
                                      ▼                               ▼
   ┌──────────────────────────── Azure ────────────────────────────────────────────────┐
   │  ACR (images)     Key Vault (app secrets, kubeconfig)     Terraform Cloud (state)  │
   │                                                                                    │
   │  Spot VM ── k3s ─┬─ ingress-nginx  ─ cert-manager (Let's Encrypt, HTTP-01)         │
   │                  ├─ External Secrets Operator ── managed identity ──► Key Vault/ACR│
   │                  └─ namespaces: optifarm-dev | optifarm-staging | optifarm-prod    │
   │                       each: frontend · api · timescaledb (+ device ingestion)      │
   └────────────────────────────────────────────────────────────────────────────────────┘
```

Each environment is a namespace with its own database, secrets, and hostname. For the MVP all three share one k3s node to keep costs down. The pipelines are already structured per environment, so an environment can move to its own cluster (or to AKS via `create_aks`) without changing the deploy logic.

---

## Repository layout

```
.
├── api/                         FastAPI backend
│   ├── routes/ services/        auth, fields, moisture readings, users
│   ├── migrations/              Alembic migrations (appschema)
│   ├── tests/unit|integration/  pytest suites (markers: unit, integration)
│   └── scripts/                 run-unit-tests.sh, run-integration-tests.sh
├── farmapp-frontend/            React 19 + TypeScript + Vite + Ant Design
│   ├── src/components/LiveView/ sensor grid and soil-moisture heatmap
│   ├── docker/                  runtime config injection (API_BASE_URL)
│   └── tests/unit|e2e/          Vitest and Playwright
├── ingest/                      device telemetry: bridge.py (MQTT→Kafka), consumer.py
│                                (Kafka→TimescaleDB), dynsec_sync.py (broker credentials)
├── simulator/                   simulated field devices publishing to MQTT
├── db/                          SQLAlchemy models (schema owned by Alembic)
├── infrastructure/
│   ├── azure-pipelines.yml      infrastructure pipeline (Terraform + Ansible)
│   ├── terraform/               root module + modules/{acr,keyvault,vm,aks}
│   └── ansible/                 install-k3s-stack.yml + Jinja2 templates
├── pipelines/
│   ├── pr-validation.yml        PR build validation
│   ├── azure-pipelines.yml      CI/CD (build, push, deploy)
│   ├── templates/               deploy-k3s.yml (per env), deploy-simulator.yml (on demand)
│   ├── charts/                  Helm charts: backend, frontend, timescaledb,
│   │                            kafka, mosquitto, ingest, simulator
│   └── manifests/ingress.yml    shared HTTPS ingress
├── .gitleaks.toml               secret-scan allowlist
└── .trivyignore.yaml            time-boxed risk acceptances
```

---

## Tech stack

| Area | Tools |
|---|---|
| Cloud | Azure: ACR, Key Vault, Linux Spot VM, VNet/NSG, managed identities, optional AKS |
| Infrastructure as code | Terraform 1.15 (azurerm, azuread, random, tls), Terraform Cloud remote state, Ansible |
| Kubernetes | k3s, Helm, ingress-nginx, cert-manager, External Secrets Operator |
| CI/CD | Azure DevOps YAML pipelines, self-hosted Linux agent, container jobs, environments |
| Security | Workload Identity Federation, Gitleaks, Semgrep, Bandit, Trivy, tfsec |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, JWT auth, pytest |
| Frontend | React 19, TypeScript, Vite, Ant Design, Leaflet, Vitest, Playwright |
| Data | TimescaleDB (PostgreSQL 18) |

---

## Infrastructure automation

All cloud resources and cluster bootstrapping are code, and both run through `infrastructure/azure-pipelines.yml`. The pipeline triggers on changes under `infrastructure/` and also runs Validate and Plan on pull requests, so infrastructure changes are reviewed with their plan output before merge.

### Terraform

`infrastructure/terraform/` is one root configuration composed of four reusable modules:

| Module | Provisions |
|---|---|
| `acr` | Azure Container Registry |
| `keyvault` | RBAC-mode Key Vault with soft delete and purge protection. It also **generates per-environment secrets** (`postgres-password-<env>`, `jwt-secret-key-<env>`) with `random_password`, so no human ever creates or sees them. |
| `vm` | Spot Linux VM (`Standard_D4as_v5`) with generated SSH key, VNet, subnet, NSG, public IP, a user-assigned managed identity for workloads, and a nightly auto-shutdown schedule |
| `aks` | AKS cluster with a system pool and an autoscaling user pool, Azure CNI, and AcrPull for the kubelet identity |

Design points:

- **Feature flags.** Each module is created with `count` and toggled by `create_acr`, `create_keyvault`, `create_vm`, and `create_aks`, supplied from a variable group. The same code can stand up the full stack, a subset, or switch from k3s to AKS.
- **Cross-module wiring at the root.** The root module connects modules through outputs rather than data lookups. The VM's workload identity gets `Key Vault Secrets User` on the vault and `AcrPull` on the registry. The AKS kubelet identity gets `AcrPull` when both exist.
- **Remote state** in Terraform Cloud, so pipeline runs and local runs share one locked state.
- **Pinned versions** for Terraform (1.15.8), providers (`~>` constraints), and tfsec.

### Infrastructure pipeline

| Stage | Runs on | What it does |
|---|---|---|
| **Validate** | PRs and pushes | `terraform fmt -check -recursive`, **tfsec** (HIGH/CRITICAL fail the build), `init`, `validate` |
| **Plan** | PRs and pushes | `terraform plan` with feature flags; the plan file is published as a pipeline artifact |
| **ApplyDev** | merge to `develop` | Applies the **exact saved plan** through the `terraform-dev` environment |
| **InstallK3sDev** | after ApplyDev | Ansible bootstrap of the cluster (see below) |
| **ApplyStaging / InstallK3sStaging** | merge to `main` | Same flow through `terraform-staging` |
| **ApplyProd / InstallK3sProd** | after staging | Same flow through `terraform-prod` |
| **Destroy** | manual (`destroy=true`) | `terraform destroy` behind its own `terraform-destroy` environment |

Applying the published plan artifact, rather than re-planning at apply time, guarantees that what was reviewed is what gets applied. The apply and destroy stages are Azure DevOps deployment jobs bound to environments, so approvals and checks can be attached per environment.

**Authentication** uses a Workload Identity Federation service connection. Inside `AzureCLI@2`, the pipeline exchanges the OIDC token for a short-lived ARM access token (`az account get-access-token`) and passes it to the azurerm provider as `ARM_ACCESS_TOKEN`. There is no client secret to store or rotate.

### Ansible cluster bootstrap

After Terraform creates the VM, the pipeline reads its public IP from Azure and its SSH key and identity IDs from Terraform outputs. It then generates an inventory on the fly and runs `infrastructure/ansible/playbooks/install-k3s-stack.yml`. The playbook is idempotent (it checks before installing and uses `helm upgrade --install`) and:

1. Installs the k3s server with TLS SANs for the public IP (Traefik disabled) and waits for the node to be Ready
2. Installs Helm and adds the ingress-nginx, external-secrets, and jetstack chart repositories
3. Installs **ingress-nginx**
4. Creates the `optifarm-dev`, `optifarm-staging`, and `optifarm-prod` namespaces
5. Installs **External Secrets Operator** (pinned 2.11.0) and renders, from Jinja2 templates:
   - a `ClusterSecretStore` backed by Key Vault, authenticated by the VM's managed identity through IMDS
   - an `ACRAccessToken` `ClusterGenerator` that mints short-lived registry tokens
   - an `acr-pull-secret` `ExternalSecret` in every app namespace, refreshed hourly
6. Installs **cert-manager** (pinned v1.21.2) with two Let's Encrypt `ClusterIssuer`s, `letsencrypt` and `letsencrypt-test`
7. Waits for each component to report Ready, then fetches the kubeconfig and rewrites it to the public endpoint

The pipeline verifies the node with the fetched kubeconfig and stores it in Key Vault as `kubeconfig-<env>`. That secret is the only handoff from the infrastructure pipeline to the application pipeline.

---

## PR build validation

`pipelines/pr-validation.yml` is attached to `develop` and `main` as an Azure Repos **Build Validation branch policy**. Every check is blocking: a PR can only complete when all stages pass. The pipeline never deploys.

Stages declare no dependencies on each other, so they run in parallel when agents are available:

| Stage | Checks |
|---|---|
| **Backend** | `compileall`, **Bandit** SAST (high severity), unit tests with coverage; then, in a separate job with a **TimescaleDB service container**: wait for the database, **Alembic migration round-trip** (`upgrade head → downgrade base → upgrade head`, plus offline SQL rendering), and integration tests |
| **Frontend** | `npm ci` with a lockfile-keyed cache, ESLint, `tsc` type check, Vitest with coverage, production `vite build` |
| **Images** | Builds both Docker images and scans them with **Trivy** (HIGH/CRITICAL with an available fix fail); PR images are always removed afterwards |
| **Security** | **Gitleaks** on the PR's commits only (`origin/<target>..HEAD`), **Semgrep** SAST (Python, TypeScript, React, Dockerfile rules), **Trivy** dependency scan of `requirements.txt` and `package-lock.json`, **Trivy IaC** scan of Helm charts, Terraform, and Dockerfiles |
| **Manifests** | `helm lint` and `helm template` for all three charts; renders `ingress.yml` with the same substitution the deploy uses and asserts the host and TLS secret |
| **Report** | Merges backend unit, backend integration, and frontend coverage into one published report |
| **QualityGate** | SonarQube analysis and quality gate, behind the `enableSonar` parameter until a server is provisioned |

Engineering details:

- **Reproducible jobs.** Backend and frontend jobs run as container jobs in pinned images (`python:3.12-slim`, `node:22-bookworm`), and every scanner runs as a pinned Docker image. The self-hosted agent needs only Docker, with no tool caches and no sudo.
- **Test results are first-class.** JUnit results are published with `failTaskOnFailedTests`, so failures show in the Azure DevOps Tests tab, not just in logs.
- **Governed risk acceptance.** Findings can only be suppressed in `.trivyignore.yaml`, and every entry requires a justification (`statement`) and an expiry date (`expired_at`). Exceptions are reviewed in PRs like any other change and lapse automatically.

---

## Continuous delivery

`pipelines/azure-pipelines.yml` runs on merges to `develop` and `main` and on `v*` tags, filtered to application paths. It assumes PR validation has passed, so it focuses on building and deploying.

### Promotion flow

| Trigger | Deploys to | Namespace / host |
|---|---|---|
| Merge to `develop` | dev | `optifarm-dev` · `https://<vm-ip>.sslip.io` |
| Merge to `main` | staging | `optifarm-staging` · `https://staging.<vm-ip>.sslip.io` |
| Tag `v*` | prod | `optifarm-prod` · `https://prod.<vm-ip>.sslip.io` |

**Build stage.** The pipeline builds the API and frontend images in parallel jobs and pushes them to ACR, tagged with the immutable build ID. The frontend image is environment-agnostic: an entrypoint script writes `config.js` from `API_BASE_URL` at container start, so **the same image is promoted unchanged** through every environment.

**Deploy stages.** All three use one reusable template, `pipelines/templates/deploy-k3s.yml`, bound to Azure DevOps environments for approvals. Each deploy:

1. Pulls `kubeconfig-<env>` from Key Vault into a temp file that is deleted on exit
2. `helm upgrade --install` for **TimescaleDB** (StatefulSet with a PVC)
3. `helm upgrade --install` for the **backend**. A `migrate` initContainer runs `alembic upgrade head` before the API starts; if it fails, `--wait` fails and the previous pods keep serving
4. Prints the migration log and waits for every `ExternalSecret` to report Ready
5. `helm upgrade --install` for the **frontend**
6. Renders the shared ingress with the environment's hostname and issuer, then applies it
7. Waits for cert-manager to issue the TLS certificate; on failure it dumps the Certificate, Order, and Challenge state for diagnosis
8. **Smoke tests:** both rollouts complete, `GET https://<host>/api/health` succeeds, and plain HTTP returns a `308` redirect to HTTPS

Every Helm release uses `--wait --timeout 5m`, so a deploy only goes green when the workloads are actually healthy. Containers define liveness and readiness probes and CPU/memory requests and limits, and the API image runs as an unprivileged user (UID 10001).

---

## Secrets management

No application secret is written by hand, committed, or passed through pipeline variables:

| Secret | Created by | Consumed by |
|---|---|---|
| DB password, JWT signing key (per env) | Terraform `random_password` → Key Vault | ESO → Kubernetes Secret → pod env |
| ACR pull credentials | ESO `ACRAccessToken` generator (short-lived, hourly refresh) | `imagePullSecrets` in every namespace |
| Cluster kubeconfig | Ansible fetch → `az keyvault secret set` | CD pipeline, per deploy, deleted on exit |
| Azure credentials for pipelines | none: Workload Identity Federation (OIDC) | Infrastructure and CD pipelines |
| Terraform Cloud token | Secret variable in `optifarm-terraform-variables` | Terraform init |

In-cluster access to Key Vault and ACR uses the VM's user-assigned managed identity through IMDS, scoped by Terraform to `Key Vault Secrets User` and `AcrPull`.

---

## Database migrations

The `appschema` schema is managed with [Alembic](https://alembic.sqlalchemy.org/) migrations in `api/migrations/versions/`.

- **Deploy:** the backend pod runs `alembic upgrade head` in its `migrate` initContainer before the API starts. If a migration fails, the new pods don't start and the previous version keeps serving.
- **PR validation:** each PR runs upgrade → downgrade → upgrade against a throwaway TimescaleDB.

To change the schema:

```bash
cd api
alembic revision -m "add sensor battery column"   # creates migrations/versions/<rev>_add_sensor_battery_column.py
# write upgrade() and downgrade() (op.add_column(...) or op.execute("...SQL..."))
alembic upgrade head                                # test locally (reads DATABASE_URL from ../.env)
```

Never edit a migration that has already been deployed. Add a new one instead.

---

## HTTPS

Each environment is served over HTTPS with a browser-trusted [Let's Encrypt](https://letsencrypt.org/) certificate. No domain purchase is needed: hostnames use [sslip.io](https://sslip.io), which resolves `<ip>.sslip.io` to `<ip>`.

- The infrastructure pipeline installs **cert-manager** and two ClusterIssuers. Their names refer to Let's Encrypt's servers, not to app environments:
  - `letsencrypt`: the real CA, issuing trusted certificates. Every app environment uses it.
  - `letsencrypt-test`: Let's Encrypt's test CA. Its certificates aren't trusted, but its rate limits are very high. Use it only to try out the flow (set `clusterIssuer: letsencrypt-test` on a deploy stage).
- `pipelines/manifests/ingress.yml` carries the `cert-manager.io/cluster-issuer` annotation and a `tls` block. cert-manager solves the HTTP-01 challenge on port 80 and stores the certificate in `Secret/optifarm-tls`. Plain HTTP redirects to HTTPS.
- Certificates last 90 days and renew automatically about 30 days before expiry. The VM is a Spot instance with a nightly auto-shutdown, so it has to be running at some point during that window.

**Rate limits:** sslip.io and nip.io are the same service with separate Let's Encrypt rate-limit pools (250,000 certificates per week each, shared by all users). If issuance ever fails with a rate-limit error, set `ingressDomain: nip.io` on the deploy stages in `pipelines/azure-pipelines.yml`.

To troubleshoot: `kubectl describe certificate,order,challenge -n optifarm-<env>`.

---

## Field-device ingestion

```
device ──MQTT/TLS──► Mosquitto ──► mqtt-bridge ──► Kafka telemetry.raw ──► ingest-consumer ──► moisturedata
         deviceid +               (key = deviceid)  (6 partitions)          (batch upsert,     (hypertable)
         passkey                                    telemetry.dlq ◄──────── commit after DB)
```

- **Devices** are registered with `POST /api/devices/` (optionally with a `fieldid`). Every device belongs to the calling user. The response contains the device's **passkey once**; only its PBKDF2-SHA512 hash is stored in `appschema.devices`. `POST /api/devices/{id}/rotate-passkey` issues a new one and `DELETE /api/devices/{id}` disables the device.
- **Broker credentials** are kept in step with that table. The API pushes each change to the running broker straight away (Mosquitto dynamic-security, `$CONTROL/dynamic-security/v1`), and on every broker start the `dynsec-sync` initContainer rebuilds the full config from the database.
- **MQTT contract:** username = `deviceid`, password = passkey; a device can only publish to `optifarm/v1/devices/<deviceid>/telemetry`. Payload: `{"ts": "2026-10-12T10:00:00Z", "readings": {"moisture": {"m1_1": 31.4, "m1_2": 32.34}}}`. `ts` is optional (the bridge's receive time is used without it); `{"batch": [...]}` sends several timestamped readings at once. Use QoS 1.
- **Moisture grid:** every device is assigned to a field (`fieldid` is required; `PATCH /api/devices/{id}` moves it). A reading holds one value per grid cell of that field, keyed `m<row>_<col>` (1-based), with rows = floor(fieldlength / cropinterval) and cols = floor(fieldbreadth / cropinterval); a 2 × 2 m field at 0.1 m spacing is 20 × 20 cells. Any subset of cells may be sent, and cells sent again with the same `ts` are merged into that reading, so large grids can be split across messages (the broker accepts up to 900 kB per message). Cells outside the grid send the message to the DLQ. Readings from before this format are kept in `moisture_legacy`.
- **Ordering and duplicates:** messages are keyed by device ID, so each device's readings stay in order in one partition. Rows are unique on `(deviceid, rtctime)` and inserted with `ON CONFLICT DO NOTHING`, so redeliveries are harmless. The bridge acknowledges MQTT messages only after Kafka has them, and the consumer commits Kafka offsets only after the database commit.
- **Rejected messages** (invalid JSON or schema, implausible timestamps, unknown or disabled devices) go to `telemetry.dlq` with the reason in the `error` header.
- **Environments:** ingestion is enabled per deploy stage (`ingestionEnabled`, dev only for now). Devices connect to `mqtt.<ingress-host>` on port 8883 with a Let's Encrypt certificate. Only one environment runs on the VM at a time, so they all use 8883. Before enabling an environment, apply Terraform so Key Vault has `mqtt-admin-password-<env>` and `mqtt-bridge-password-<env>` and the NSG allows 8883.
- **Simulator:** not deployed by normal runs. Queue the CD pipeline with **Deploy device data simulator** checked (dev or staging). Devices and their Key Vault passkeys are listed in `pipelines/charts/simulator/values-<env>.yaml`; see `pipelines/charts/simulator/README.md`.

Run the whole flow locally with Docker:

```bash
docker compose -f docker-compose.ingest.yml up -d --build      # API on :8000, MQTT on :1883
# register a user and devices via http://localhost:8000/docs, then:
cp simulator/devices.example.yaml simulator/devices.yaml       # fill in deviceids + passkeys
docker compose -f docker-compose.ingest.yml --profile sim up -d simulator
```

---

## Azure DevOps setup

One-time configuration that lives in Azure DevOps rather than in code:

| Item | Name | Purpose |
|---|---|---|
| Agent pool | `Exp-Agent` | Self-hosted Linux agent with Docker |
| Service connection | `terraform-arm-connection` | Azure Resource Manager, **Workload Identity Federation**. Contributor plus User Access Administrator (Terraform creates role assignments) |
| Service connection | `optifarm-acr-connection` | Docker registry connection for pushing images |
| Service connection | `farmapp-sonarqube` | Optional, for the SonarQube quality gate |
| Variable group | `optifarm-terraform-variables` | `TFE_TOKEN` (secret), `resource_grp`, `location`, `vm_name`, `key_vault_name`, `create_*` flags |
| Variable group | `optifarm-variables` | `key_vault_name` for the deploy pipeline |
| Environments | `terraform-dev`, `terraform-staging`, `terraform-prod`, `terraform-destroy` | Approval gates for infrastructure changes |
| Environments | `dev`, `staging`, `prod` | Approval gates for application deploys |
| Branch policy | `develop`, `main` | Build Validation → `pipelines/pr-validation.yml` (required) |

For Azure Repos Git, the `pr:` block in YAML is ignored. The branch policy decides when PR validation runs, so set its path filter there.

---

## Local development

```bash
# Backend unit tests (no database needed)
cd api && pip install -r requirements-dev.txt && ./scripts/run-unit-tests.sh

# Ingest / simulator unit tests
cd ingest && pip install -r requirements-dev.txt && python -m pytest
cd simulator && pip install -r requirements-dev.txt && python -m pytest

# Backend integration tests (needs DATABASE_URL pointing at a TimescaleDB/PostgreSQL)
./scripts/run-integration-tests.sh

# Frontend
cd farmapp-frontend && npm ci
npm run lint && npm run typecheck && ./scripts/run-unit-tests.sh
./scripts/run-e2e-tests.sh   # Playwright end-to-end tests

# Infrastructure (requires a Terraform Cloud token and Azure login)
cd infrastructure/terraform && terraform init && terraform plan
```

---

## Known limitations and roadmap

These are tracked deliberately, most as time-boxed exceptions in `.trivyignore.yaml`:

- **NSG lockdown:** SSH (22) and the Kubernetes API (6443) are open to the internet for the hosted agent. Restrict them to known ranges or move to a private endpoint.
- **Key Vault network ACLs:** public network access is enabled; add network restrictions.
- **Frontend container user:** nginx still runs as root; switch to `nginx-unprivileged`.
- **Single-node cluster:** all environments share one Spot VM. Split environments or move to AKS (`create_aks = true`) for isolation and availability.
- **SonarQube:** the quality-gate stage is ready but disabled until a server exists.
- **E2E in CI:** Playwright tests run locally; add them as a post-deploy stage against dev.

---

## License

[MIT](LICENSE)