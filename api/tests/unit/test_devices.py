"""Unit tests for the /devices routes and device_service (database and broker mocked)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from config.database import get_db
from main import app
from middleware.auth import get_current_user
from routes import devices as devices_routes
from services import device_service, mqtt_admin

USER = {"userid": 100001}
NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)


def _device(**overrides):
    device = {"deviceid": "dev-001", "devicename": "North corner", "userinfo": USER["userid"], "fieldid": 200001,
              "status": "active", "last_seen": None, "created_at": NOW}
    device.update(overrides)
    return device


FIELD = {"fieldid": 200001, "userid": USER["userid"], "fieldlength": 2.0,
         "fieldbreadth": 2.0, "cropinterval": 0.1}


@pytest.fixture
def client(monkeypatch):
    # Every request below is for a field the user owns, unless a test overrides it
    monkeypatch.setattr(devices_routes, "get_field_by_id", lambda db, fieldid, userid: FIELD)
    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestDeviceRoutes:
    def test_create_returns_passkey_and_topic(self, client, monkeypatch):
        received = {}

        def fake_create(db, userid, deviceid, devicename, fieldid):
            received.update(devicename=devicename)
            return _device(devicename=devicename), "the-passkey"
        monkeypatch.setattr(device_service, "create_device", fake_create)
        response = client.post("/devices/", json={"devicename": "  North corner  ", "fieldid": 200001})
        assert response.status_code == 201
        body = response.json()
        assert received == {"devicename": "North corner"}     # trimmed
        assert body["devicename"] == "North corner"
        assert body["passkey"] == "the-passkey"
        assert body["userinfo"] == USER["userid"]
        assert body["mqtt_topic"] == "optifarm/v1/devices/dev-001/telemetry"

    @pytest.mark.parametrize("bad_id", ["a/b", "dev+1", "dev#", "ab", "-dev"])
    def test_rejects_ids_unsafe_for_mqtt(self, client, bad_id):
        body = {"devicename": "n", "deviceid": bad_id, "fieldid": 200001}
        assert client.post("/devices/", json=body).status_code == 422

    def test_field_is_required(self, client):
        assert client.post("/devices/", json={"devicename": "n"}).status_code == 422

    @pytest.mark.parametrize("name", [None, "", "   ", "x" * 101])
    def test_name_is_required_and_limited(self, client, name):
        body = {"fieldid": 200001} if name is None else {"devicename": name, "fieldid": 200001}
        assert client.post("/devices/", json=body).status_code == 422

    def test_unknown_field_is_404(self, client, monkeypatch):
        monkeypatch.setattr(devices_routes, "get_field_by_id", lambda db, fieldid, userid: None)
        assert client.post("/devices/", json={"devicename": "n", "fieldid": 1}).status_code == 404

    def test_duplicate_id_is_409(self, client, monkeypatch):
        def raise_exists(*args, **kwargs):
            raise device_service.DeviceExistsError("dev-001")
        monkeypatch.setattr(device_service, "create_device", raise_exists)
        body = {"devicename": "n", "deviceid": "dev-001", "fieldid": 200001}
        assert client.post("/devices/", json=body).status_code == 409

    def test_broker_failure_is_503(self, client, monkeypatch):
        def raise_broker(*args, **kwargs):
            raise mqtt_admin.BrokerError("down")
        monkeypatch.setattr(device_service, "create_device", raise_broker)
        assert client.post("/devices/", json={"devicename": "n", "fieldid": 200001}).status_code == 503

    def test_list_never_includes_passkey(self, client, monkeypatch):
        monkeypatch.setattr(device_service, "get_devices_by_user", lambda db, userid, **kw: [_device()])
        body = client.get("/devices/").json()
        assert body[0]["deviceid"] == "dev-001" and body[0]["devicename"] == "North corner"
        assert "passkey" not in body[0]

    def test_list_filters_are_passed_through(self, client, monkeypatch):
        seen = []
        monkeypatch.setattr(device_service, "get_devices_by_user",
                            lambda db, userid, **kw: seen.append(kw) or [])
        client.get("/devices/")
        client.get("/devices/?fieldid=200001&include_disabled=true")
        assert seen == [{"fieldid": None, "include_disabled": False},
                        {"fieldid": 200001, "include_disabled": True}]

    def test_rotate_unknown_device_is_404(self, client, monkeypatch):
        monkeypatch.setattr(device_service, "rotate_passkey", lambda db, deviceid, userid: None)
        assert client.post("/devices/dev-404/rotate-passkey").status_code == 404

    def test_disable(self, client, monkeypatch):
        monkeypatch.setattr(device_service, "disable_device",
                            lambda db, deviceid, userid: _device(status="disabled"))
        assert client.delete("/devices/dev-001").json()["status"] == "disabled"


@pytest.mark.unit
class TestDeviceServiceBrokerConsistency:
    def _db(self):
        db = MagicMock()
        row = MagicMock()
        row._mapping = _device()
        db.execute.return_value.fetchone.return_value = row
        return db

    def test_create_stores_hash_not_passkey_and_commits(self, monkeypatch):
        pushed = {}
        monkeypatch.setattr(mqtt_admin, "create_device_client",
                            lambda deviceid, passkey: pushed.update(deviceid=deviceid, passkey=passkey))
        db = self._db()
        device, passkey = device_service.create_device(db, USER["userid"], "dev-001", "North corner", 200001)

        params = db.execute.call_args.args[1]
        assert params["userinfo"] == USER["userid"]
        assert params["devicename"] == "North corner"
        assert passkey not in params.values()
        assert params["iterations"] == 1000
        assert pushed == {"deviceid": "dev-001", "passkey": passkey}
        db.commit.assert_called_once()

    def test_create_generates_id_when_missing(self, monkeypatch):
        monkeypatch.setattr(mqtt_admin, "create_device_client", lambda deviceid, passkey: None)
        db = self._db()
        device_service.create_device(db, USER["userid"], None, "n", 200001)
        assert db.execute.call_args.args[1]["deviceid"].startswith("dev-")

    def test_create_rolls_back_when_broker_rejects(self, monkeypatch):
        def reject(deviceid, passkey):
            raise mqtt_admin.BrokerError("nope")
        monkeypatch.setattr(mqtt_admin, "create_device_client", reject)
        db = self._db()
        with pytest.raises(mqtt_admin.BrokerError):
            device_service.create_device(db, USER["userid"], "dev-001", "n", 200001)
        db.rollback.assert_called_once()
        db.commit.assert_not_called()

    def test_create_removes_broker_client_when_commit_fails(self, monkeypatch):
        monkeypatch.setattr(mqtt_admin, "create_device_client", lambda deviceid, passkey: None)
        removed = []
        monkeypatch.setattr(mqtt_admin, "delete_device_client", removed.append)
        db = self._db()
        db.commit.side_effect = RuntimeError("db gone")
        with pytest.raises(RuntimeError):
            device_service.create_device(db, USER["userid"], "dev-001", "n", 200001)
        assert removed == ["dev-001"]

    def test_rotate_rolls_back_when_broker_rejects(self, monkeypatch):
        def reject(deviceid, passkey):
            raise mqtt_admin.BrokerError("nope")
        monkeypatch.setattr(mqtt_admin, "set_device_passkey", reject)
        db = self._db()
        with pytest.raises(mqtt_admin.BrokerError):
            device_service.rotate_passkey(db, "dev-001", USER["userid"])
        db.commit.assert_not_called()

    def test_list_query_skips_disabled_unless_asked(self):
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        device_service.get_devices_by_user(db, USER["userid"], fieldid=200001)
        sql, params = str(db.execute.call_args.args[0]), db.execute.call_args.args[1]
        assert "status = 'active'" in sql and "fieldid = :fieldid" in sql
        assert params == {"userid": USER["userid"], "fieldid": 200001, "include_disabled": False}
