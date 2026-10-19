"""Unit tests for payload parsing, the consumer batch logic and dynsec_sync (no Kafka/DB/broker)."""

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import consumer
import dynsec_sync
from config import Settings, deviceid_from_topic
from consumer import DeviceInfo, prepare_batch, process

pytestmark = pytest.mark.unit

NOW = datetime.now(timezone.utc).replace(microsecond=0)
SETTINGS = Settings(mqtt_admin_password="admin-pw", mqtt_bridge_password="bridge-pw")


class FakeMessage:
    def __init__(self, deviceid, payload, offset=0, partition=0, received_at=NOW):
        self._key = deviceid.encode() if deviceid else None
        self._value = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self._offset = offset
        self._partition = partition
        self._headers = [("received_at", received_at.isoformat().encode())]

    def key(self): return self._key
    def value(self): return self._value
    def headers(self): return self._headers
    def timestamp(self): return (1, int(NOW.timestamp() * 1000))
    def topic(self): return "telemetry.raw"
    def partition(self): return self._partition
    def offset(self): return self._offset
    def error(self): return None


class FakeDirectory:
    def __init__(self, devices):
        self.devices = devices

    def lookup(self, deviceids):
        return {d: self.devices.get(d) for d in deviceids}


DEVICES = FakeDirectory({
    "dev-001": DeviceInfo(userinfo=100001, fieldid=200001, active=True, grid=(20, 20)),
    "dev-off": DeviceInfo(userinfo=100001, fieldid=200001, active=False, grid=(20, 20)),
    "dev-nofield": DeviceInfo(userinfo=100001, fieldid=None, active=True, grid=None),
})


class TestTopic:
    @pytest.mark.parametrize("topic, expected", [
        ("optifarm/v1/devices/dev-001/telemetry", "dev-001"),
        ("optifarm/v1/devices/a/b/telemetry", None),
        ("optifarm/v1/devices//telemetry", None),
        ("other/dev-001/telemetry", None),
        ("optifarm/v1/devices/dev-001/status", None),
    ])
    def test_deviceid_from_topic(self, topic, expected):
        assert deviceid_from_topic(SETTINGS, topic) == expected


class TestPrepareBatch:
    def test_device_timestamp_is_used_and_owner_attached(self):
        ts = NOW - timedelta(minutes=5)
        msg = FakeMessage("dev-001", {"ts": ts.isoformat(), "readings": {"moisture": {"m1_1": 31.4}}})
        result = prepare_batch([msg], DEVICES, SETTINGS)
        assert result.rejected == []
        assert result.rows == [{"moisture": '{"m1_1": 31.4}', "rtctime": ts, "deviceid": "dev-001",
                                "userinfo": 100001, "fieldid": 200001}]

    def test_missing_ts_falls_back_to_receive_time(self):
        msg = FakeMessage("dev-001", {"readings": {"moisture": {"m1_1": 20}}})
        assert prepare_batch([msg], DEVICES, SETTINGS).rows[0]["rtctime"] == NOW

    def test_batch_payload_is_flattened(self):
        items = [{"ts": (NOW - timedelta(minutes=i)).isoformat(), "readings": {"moisture": {"m1_1": i}}}
                 for i in range(3)]
        result = prepare_batch([FakeMessage("dev-001", {"batch": items})], DEVICES, SETTINGS)
        assert [json.loads(r["moisture"])["m1_1"] for r in result.rows] == [0, 1, 2]
        assert result.last_seen == {"dev-001": NOW}

    @pytest.mark.parametrize("payload, reason", [
        (b"not json", "invalid payload"),
        ({"readings": {}}, "invalid payload"),
        ({"readings": {"moisture": {"m1_1": "NaN"}}}, "invalid payload"),
        ({"ts": "2026-10-12T10:00:00", "readings": {"moisture": {"m1_1": 1}}}, "invalid payload"),
        ({"batch": [{"readings": {"moisture": {"m1_1": 1}}}]}, "invalid payload"),
        ({"readings": {"moisture": {"m1_1": 1}}, "batch": []}, "invalid payload"),
        ({"ts": "1970-01-01T00:00:00Z", "readings": {"moisture": {"m1_1": 1}}}, "outside the accepted window"),
        ({"ts": (NOW + timedelta(days=1)).isoformat(), "readings": {"moisture": {"m1_1": 1}}},
         "outside the accepted window"),
    ])
    def test_bad_payloads_go_to_dlq(self, payload, reason):
        result = prepare_batch([FakeMessage("dev-001", payload)], DEVICES, SETTINGS)
        assert result.rows == []
        assert reason in result.rejected[0][1]

    @pytest.mark.parametrize("deviceid, reason", [
        ("dev-unknown", "unknown device"),
        ("dev-off", "device disabled"),
        ("dev-nofield", "device has no field assigned (PATCH /devices/{id})"),
    ])
    def test_unknown_and_disabled_devices_go_to_dlq(self, deviceid, reason):
        result = prepare_batch([FakeMessage(deviceid, {"readings": {"moisture": {"m1_1": 1}}})], DEVICES, SETTINGS)
        assert result.rows == [] and result.rejected[0][1] == reason

    def test_full_and_partial_grids_are_stored(self):
        full = {f"m{r}_{c}": 30.0 for r in range(1, 21) for c in range(1, 21)}
        result = prepare_batch([FakeMessage("dev-001", {"readings": {"moisture": full}}),
                                FakeMessage("dev-001", {"readings": {"moisture": {"m20_20": 5}}}, offset=1)],
                               DEVICES, SETTINGS)
        assert result.rejected == []
        assert len(json.loads(result.rows[0]["moisture"])) == 400

    @pytest.mark.parametrize("cells, bad", [
        ({"m1_1": 1, "m21_1": 2}, "m21_1"),          # row 21 in a 20-row field
        ({"m1_21": 2}, "m1_21"),                       # column 21
    ])
    def test_cells_outside_grid_go_to_dlq(self, cells, bad):
        result = prepare_batch([FakeMessage("dev-001", {"readings": {"moisture": cells}})], DEVICES, SETTINGS)
        assert result.rows == []
        assert "20 x 20 grid" in result.rejected[0][1] and bad in result.rejected[0][1]

    @pytest.mark.parametrize("cells", [{}, {"m11": 1}, {"m0_1": 1}, {"m1_1": None}, 31.4])
    def test_malformed_cells_go_to_dlq(self, cells):
        result = prepare_batch([FakeMessage("dev-001", {"readings": {"moisture": cells}})], DEVICES, SETTINGS)
        assert result.rows == [] and "invalid payload" in result.rejected[0][1]

    def test_one_bad_message_does_not_drop_the_rest(self):
        msgs = [FakeMessage("dev-001", {"readings": {"moisture": {"m1_1": 1}}}, offset=0),
                FakeMessage("dev-001", b"{", offset=1),
                FakeMessage("dev-001", {"ts": (NOW - timedelta(seconds=1)).isoformat(),
                                        "readings": {"moisture": {"m1_1": 2}}}, offset=2)]
        result = prepare_batch(msgs, DEVICES, SETTINGS)
        assert [json.loads(r["moisture"])["m1_1"] for r in result.rows] == [1, 2]
        assert [m.offset() for m, _ in result.rejected] == [1]


class TestProcessCommitOrder:
    def test_offsets_committed_after_store(self, monkeypatch):
        calls = []
        monkeypatch.setattr(consumer, "store", lambda engine, batch: calls.append("store"))
        kafka = MagicMock()
        kafka.commit.side_effect = lambda **kw: calls.append("commit")
        process([FakeMessage("dev-001", {"readings": {"moisture": {"m1_1": 1}}})],
                kafka, MagicMock(), None, DEVICES, SETTINGS)
        assert calls == ["store", "commit"]

    def test_offsets_not_committed_when_db_write_fails(self, monkeypatch):
        def fail(engine, batch):
            raise RuntimeError("db down")
        monkeypatch.setattr(consumer, "store", fail)
        kafka = MagicMock()
        with pytest.raises(RuntimeError):
            process([FakeMessage("dev-001", {"readings": {"moisture": {"m1_1": 1}}})],
                    kafka, MagicMock(), None, DEVICES, SETTINGS)
        kafka.commit.assert_not_called()

    def test_rewind_seeks_to_first_offset_per_partition(self):
        kafka = MagicMock()
        consumer.rewind(kafka, [FakeMessage("a", b"", offset=7, partition=0),
                                FakeMessage("a", b"", offset=5, partition=0),
                                FakeMessage("b", b"", offset=9, partition=1)])
        seeks = sorted((c.args[0].partition, c.args[0].offset) for c in kafka.seek.call_args_list)
        assert seeks == [(0, 5), (1, 9)]


class TestDynsecSync:
    def _device(self, deviceid, passkey):
        salt = b"s" * 64
        digest = hashlib.pbkdf2_hmac("sha512", passkey.encode(), salt, 1000, 64)
        return {"deviceid": deviceid, "passkey_hash": base64.b64encode(digest).decode(),
                "passkey_salt": base64.b64encode(salt).decode(), "passkey_iterations": 1000}

    def test_devices_get_stored_hash_and_device_role(self):
        config = dynsec_sync.build_config(SETTINGS, [self._device("dev-001", "pk")])
        client = next(c for c in config["clients"] if c["username"] == "dev-001")
        _, version, iterations, salt, digest = client["encoded_password"].split("$")
        assert (version, iterations) == ("7", "1000")
        assert base64.b64decode(digest) == hashlib.pbkdf2_hmac(
            "sha512", b"pk", base64.b64decode(salt), 1000, 64)
        assert client["roles"] == [{"rolename": "device"}]

    def test_system_clients_and_scoped_device_acl(self):
        config = dynsec_sync.build_config(SETTINGS, [])
        assert [c["username"] for c in config["clients"]] == ["admin", "bridge"]
        device_role = next(r for r in config["roles"] if r["rolename"] == "device")
        assert device_role["acls"] == [{"acltype": "publishClientSend",
                                        "topic": "optifarm/v1/devices/%u/telemetry", "allow": True}]
        assert config["defaultACLAccess"]["publishClientSend"] is False

    def test_device_cannot_take_a_system_name(self):
        config = dynsec_sync.build_config(SETTINGS, [self._device("admin", "x")])
        assert [c["roles"] for c in config["clients"] if c["username"] == "admin"] == [[{"rolename": "admin"}]]

    def test_missing_system_passwords_fail(self):
        with pytest.raises(SystemExit):
            dynsec_sync.build_config(Settings(), [])
