"""Unit tests for the moisture generator, payloads and simulator configuration."""

from datetime import datetime, timedelta, timezone

import pytest

from config import Settings, load_devices
from generator import FieldMoistureGenerator, MoistureGenerator, MoistureProfile
from main import build_payloads, make_generator

FIELD = "    field_length: 2\n    field_breadth: 2\n    crop_interval: 0.1\n"

pytestmark = pytest.mark.unit

NOON = datetime(2026, 7, 1, 13, 0, tzinfo=timezone.utc)
MIDNIGHT = datetime(2026, 7, 1, 1, 0, tzinfo=timezone.utc)


def _series(gen, start, steps, step_seconds=600):
    return [gen.next(start + timedelta(seconds=i * step_seconds), step_seconds) for i in range(steps)]


class TestGenerator:
    def test_stays_within_bounds(self):
        profile = MoistureProfile(min_value=10, max_value=40, noise=2.0)
        values = _series(MoistureGenerator(profile, seed=1), NOON, 5000)
        assert min(values) >= 10 and max(values) <= 40

    def test_dries_faster_at_midday_than_at_night(self):
        quiet = dict(noise=0, random_irrigation_per_hour=0, irrigation_threshold=0)
        day = MoistureGenerator(MoistureProfile(**quiet), seed=1)
        night = MoistureGenerator(MoistureProfile(**quiet), seed=1)
        day_drop = 35 - _series(day, NOON, 6)[-1]
        night_drop = 35 - _series(night, MIDNIGHT, 6)[-1]
        assert day_drop > night_drop > 0

    def test_irrigates_below_threshold(self):
        profile = MoistureProfile(start=18.5, irrigation_threshold=18, noise=0,
                                  random_irrigation_per_hour=0, dry_rate_per_hour=5)
        values = _series(MoistureGenerator(profile, seed=1), NOON, 3)
        assert max(values) > 25

    def test_same_seed_same_series_and_devices_differ(self):
        a = _series(MoistureGenerator(MoistureProfile(), seed="dev-001"), NOON, 50)
        b = _series(MoistureGenerator(MoistureProfile(), seed="dev-001"), NOON, 50)
        c = _series(MoistureGenerator(MoistureProfile(), seed="dev-002"), NOON, 50)
        assert a == b and a != c


class TestFieldGenerator:
    def test_one_value_per_cell_within_bounds(self):
        profile = MoistureProfile(min_value=10, max_value=40)
        cells = FieldMoistureGenerator(profile, "dev-001", rows=20, cols=20).next(NOON, 600)
        assert len(cells) == 400
        assert set(cells) == {f"m{r}_{c}" for r in range(1, 21) for c in range(1, 21)}
        assert all(10 <= v <= 40 for v in cells.values())

    def test_cells_differ_but_follow_the_field(self):
        gen = FieldMoistureGenerator(MoistureProfile(noise=0), "dev-001", rows=5, cols=5, cell_spread=3)
        cells = gen.next(NOON, 600)
        assert len(set(cells.values())) > 1                    # per-cell offsets
        assert abs(sum(cells.values()) / 25 - gen.field.level) < 3   # around the field curve

    def test_same_seed_same_grid(self):
        a = FieldMoistureGenerator(MoistureProfile(), "dev-001", 4, 4).next(NOON, 600)
        b = FieldMoistureGenerator(MoistureProfile(), "dev-001", 4, 4).next(NOON, 600)
        assert a == b


class TestPayload:
    CELLS = {"m1_1": 31.4, "m1_2": 32.34, "m2_1": 12.33, "m2_2": 56.78}

    def test_with_timestamp(self):
        assert build_payloads(self.CELLS, NOON, True, 20000) == [
            {"readings": {"moisture": self.CELLS}, "ts": "2026-07-01T13:00:00Z"}]

    def test_without_timestamp(self):
        assert build_payloads(self.CELLS, NOON, False, 20000) == [{"readings": {"moisture": self.CELLS}}]

    def test_large_grid_is_split_with_the_same_ts(self):
        parts = build_payloads(self.CELLS, NOON, True, 3)
        assert [len(p["readings"]["moisture"]) for p in parts] == [3, 1]
        assert {p["ts"] for p in parts} == {"2026-07-01T13:00:00Z"}
        assert {k: v for p in parts for k, v in p["readings"]["moisture"].items()} == self.CELLS


class TestConfig:
    def test_connection_defaults_point_at_cluster_broker(self, monkeypatch):
        for var in ("MQTT_HOST", "MQTT_PORT", "MQTT_TLS"):
            monkeypatch.delenv(var, raising=False)
        settings = Settings(_env_file=None)
        assert (settings.mqtt_host, settings.mqtt_port, settings.mqtt_tls) == ("mosquitto", 1883, False)
        assert settings.mqtt_topic_prefix == "optifarm/v1/devices"

    def test_env_overrides_connection(self, monkeypatch):
        monkeypatch.setenv("MQTT_HOST", "mqtt.example.org")
        monkeypatch.setenv("MQTT_PORT", "8883")
        monkeypatch.setenv("MQTT_TLS", "true")
        settings = Settings(_env_file=None)
        assert (settings.mqtt_host, settings.mqtt_port, settings.mqtt_tls) == ("mqtt.example.org", 8883, True)

    def test_loads_devices_and_resolves_passkey_from_env(self, tmp_path, monkeypatch):
        path = tmp_path / "devices.yaml"
        path.write_text("devices:\n"
                        "  - deviceid: dev-001\n    passkey_env: PK1\n    start: 20\n    min: 5\n" + FIELD +
                        "  - deviceid: dev-002\n    passkey: inline\n    send_ts: false\n" + FIELD)
        monkeypatch.setenv("PK1", "from-env")
        devices = load_devices(str(path))
        assert [d.resolve_passkey() for d in devices] == ["from-env", "inline"]
        assert devices[1].send_ts is False
        assert make_generator(devices[0]).profile.min_value == 5
        assert devices[0].grid == (20, 20) and len(make_generator(devices[0]).offsets) == 400

    @pytest.mark.parametrize("body, error", [
        ("devices: []\n", "at least 1"),
        ("devices:\n  - deviceid: dev-001\n" + FIELD, "passkey"),
        ("devices:\n  - deviceid: a/b\n    passkey: x\n" + FIELD, "pattern"),
        ("devices:\n  - deviceid: dev-001\n    passkey: x\n", "field_length"),
        ("devices:\n  - deviceid: dev-001\n    passkey: x\n" + FIELD.replace("0.1", "0"), "greater than 0"),
        ("devices:\n  - deviceid: dev-001\n    passkey: x\n    send_ts: false\n"
         "    max_cells_per_message: 100\n" + FIELD, "share a timestamp"),
        ("devices:\n  - {deviceid: dev-001, passkey: x, field_length: 2, field_breadth: 2, crop_interval: 0.1}\n"
         "  - {deviceid: dev-001, passkey: y, field_length: 2, field_breadth: 2, crop_interval: 0.1}\n", "duplicate"),
    ])
    def test_invalid_device_files(self, tmp_path, body, error):
        path = tmp_path / "devices.yaml"
        path.write_text(body)
        with pytest.raises(ValueError, match=error):
            load_devices(str(path))

    def test_missing_passkey_env_is_reported(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PK_MISSING", raising=False)
        path = tmp_path / "devices.yaml"
        path.write_text("devices:\n  - deviceid: dev-001\n    passkey_env: PK_MISSING\n" + FIELD)
        with pytest.raises(ValueError, match="PK_MISSING"):
            load_devices(str(path))[0].resolve_passkey()
