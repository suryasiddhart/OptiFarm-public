"""Application settings loaded from environment variables.

SECURITY: All sensitive values (database_url, secret_key) MUST be
provided via environment variables or a .env file. No hardcoded secrets.

In Kubernetes, these are injected via:
  - Azure Key Vault → External Secrets Operator → optifarm-secrets K8s Secret
    (see pipelines/charts/backend/templates/externalsecret.yaml)
  - Deployment env.secretKeyRef (see pipelines/charts/backend/values.yaml)

Loading strategy:
  - Local development: Settings are loaded from a .env file (gitignored).
  - Container/Kubernetes: Settings are injected via K8s secrets as
    environment variables (secretKeyRef). The .env file is NOT present
    in the container image (see .dockerignore).
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


def _should_load_env_file() -> bool:
    """
    Determine whether to load settings from a .env file.

    Returns True only when running outside a container (i.e. local dev).
    Detection strategy:
      1. Check for the presence of /.dockerenv (Linux containers).
      2. Check the KUBERNETES_SERVICE_HOST env var (in-cluster K8s).
      3. Check for a custom IN_CONTAINER env var set by the Dockerfile.
    If none of these indicate a container environment, assume local dev
    and load from .env.
    """
    # Running inside a Docker/Linux container
    if os.path.exists("/.dockerenv"):
        return False
    # Running inside a Kubernetes pod
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return False
    # Explicitly flagged as container environment
    if os.environ.get("IN_CONTAINER", "").lower() in ("true", "1", "yes"):
        return False
    return True


class Settings(BaseSettings):
    # App
    app_name: str = "api"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    # SECURITY: MUST be set via env var DATABASE_URL or .env file.
    # No default — will fail at runtime if not provided.
    # Format: postgresql://user:password@host:port/dbname
    database_url: str = Field(
        validation_alias="DATABASE_URL",
    )
    database_schema: str = "appschema"

    # Security
    # SECURITY: MUST be set via env var SECRET_KEY or .env file.
    # No default — will fail at runtime if not provided.
    # Must be a cryptographically random string of at least 32 characters.
    secret_key: str = Field(
        validation_alias="SECRET_KEY",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Brute-force protection: lock a mobile number for login_lockout_minutes
    # after login_max_attempts failed logins (see services/login_attempt_service.py)
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file="../.env" if _should_load_env_file() else None,
        env_file_encoding="utf-8",
        # Fail if required secrets are missing at runtime
        validate_default=True,
        extra="ignore",
    )


settings = Settings()
