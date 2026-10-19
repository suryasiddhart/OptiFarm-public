"""Simulator settings.

Connection settings come from environment variables (or a .env file) and
default to the in-cluster Mosquitto service, which is also the service name
in docker-compose.ingest.yml. Devices come from a YAML file
(SIMULATOR_DEVICES_FILE); each device's passkey can be given inline or, as in
Kubernetes, through an environment variable named by `passkey_env`.

Example devices.yaml:

    devices:
      - deviceid: dev-001
        passkey_env: PASSKEY_DEV_001
        field_length: 2         # same values as the device's field in the app:
        field_breadth: 2        # the grid is floor(length / interval) rows x
        crop_interval: 0.1      # floor(breadth / interval) cols = 20 x 20 cells
        interval_seconds: 30
      - deviceid: dev-002
        passkey: "..."          # local testing only
        field_length: 1
        field_breadth: 1
        crop_interval: 0.25     # 4 x 4 cells
        send_ts: false          # behave like a device without a clock
        start: 25
"""

import os

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from grid import grid_size


class Settings(BaseSettings):
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_tls: bool = False
    mqtt_ca_file: str = ""            # empty = system CA bundle (when TLS is on)
    mqtt_topic_prefix: str = "optifarm/v1/devices"
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    mqtt_keepalive: int = 60

    simulator_devices_file: str = "devices.yaml"
    # Defaults for devices that don't set their own
    simulator_interval_seconds: float = Field(default=60.0, gt=0)
    # Start each device at a random offset within its interval, so they don't
    # all publish in the same instant.
    simulator_jitter_start: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class DeviceConfig(BaseModel):
    deviceid: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
    passkey: str | None = None
    passkey_env: str | None = None
    # The device's field (as registered in the app); sets the moisture grid
    field_length: float = Field(gt=0)
    field_breadth: float = Field(gt=0)
    crop_interval: float = Field(gt=0)
    # Cells per MQTT message; bigger grids are sent in parts with the same ts
    max_cells_per_message: int = Field(default=20000, gt=0)
    # Standard deviation of the fixed per-cell offset from the field average
    cell_spread: float = Field(default=3.0, ge=0)
    interval_seconds: float | None = Field(default=None, gt=0)
    send_ts: bool = True
    start: float | None = None
    min: float | None = None
    max: float | None = None
    seed: int | None = None

    @model_validator(mode="after")
    def has_passkey_source(self) -> "DeviceConfig":
        if not self.passkey and not self.passkey_env:
            raise ValueError(f"{self.deviceid}: set 'passkey' or 'passkey_env'")
        return self

    @model_validator(mode="after")
    def parts_need_timestamp(self) -> "DeviceConfig":
        rows, cols = self.grid
        if rows * cols > self.max_cells_per_message and not self.send_ts:
            raise ValueError(
                f"{self.deviceid}: {rows} x {cols} cells need several messages, which only "
                "merge into one reading when they share a timestamp: set send_ts: true "
                "or raise max_cells_per_message")
        return self

    @property
    def grid(self) -> tuple[int, int]:
        return grid_size(self.field_length, self.field_breadth, self.crop_interval)

    def resolve_passkey(self) -> str:
        if self.passkey:
            return self.passkey
        value = os.environ.get(self.passkey_env or "")
        if not value:
            raise ValueError(f"{self.deviceid}: environment variable {self.passkey_env} is not set")
        return value


class DevicesFile(BaseModel):
    devices: list[DeviceConfig] = Field(min_length=1)


def load_devices(path: str) -> list[DeviceConfig]:
    with open(path) as f:
        devices = DevicesFile.model_validate(yaml.safe_load(f) or {}).devices
    ids = [d.deviceid for d in devices]
    duplicates = {d for d in ids if ids.count(d) > 1}
    if duplicates:
        raise ValueError(f"duplicate deviceid(s) in {path}: {', '.join(sorted(duplicates))}")
    return devices
