"""Integration tests for authorization (field/moisture ownership) and
login brute-force protection.

Require a migrated database (DATABASE_URL) — run after `alembic upgrade head`.
"""

import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from config.settings import settings
from main import app

client = TestClient(app)
PASSWORD = "Correct-Horse-1"


def _unique_mobile() -> str:
    return "9" + uuid.uuid4().hex[:9]


def _register_and_login(mobileno: str | None = None) -> dict:
    mobileno = mobileno or _unique_mobile()
    resp = client.post("/auth/register", json={
        "firstname": "Test", "lastname": "User", "mobileno": mobileno, "password": PASSWORD,
    })
    assert resp.status_code == 201, resp.text
    resp = client.post("/auth/login", json={"mobileno": mobileno, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return {
        "mobileno": mobileno,
        "userid": body["user"]["userid"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


def _create_field(user: dict, **extra) -> dict:
    payload = {
        "fieldlength": 10, "fieldbreadth": 5, "croptype": "Rice", "cropsubtype": "Basmati",
        "cropinterval": 30, "fieldlat": 12.9, "fieldlong": 77.5, **extra,
    }
    resp = client.post("/fields/", json=payload, headers=user["headers"])
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def alice():
    return _register_and_login()


@pytest.fixture
def bob():
    return _register_and_login()


@pytest.mark.integration
class TestFieldOwnership:
    def test_owner_can_read_own_field(self, alice):
        field = _create_field(alice)
        resp = client.get(f"/fields/{field['fieldid']}", headers=alice["headers"])
        assert resp.status_code == 200
        assert resp.json()["userid"] == alice["userid"]

    def test_other_user_gets_404_for_field(self, alice, bob):
        field = _create_field(alice)
        resp = client.get(f"/fields/{field['fieldid']}", headers=bob["headers"])
        assert resp.status_code == 404

    def test_userid_in_body_is_ignored(self, alice, bob):
        field = _create_field(alice, userid=bob["userid"])
        assert field["userid"] == alice["userid"]
        listed = client.get("/fields/", headers=bob["headers"]).json()
        assert field["fieldid"] not in [f["fieldid"] for f in listed]


@pytest.mark.integration
class TestMoistureOwnership:
    def test_reading_recorded_for_caller(self, alice, bob):
        field = _create_field(alice)
        resp = client.post("/moisture/", headers=alice["headers"], json={
            "moisture": 41.5, "deviceid": "dev-1", "fieldid": field["fieldid"],
            "userinfo": bob["userid"],  # ignored
            "rtctime": "2026-10-08T10:00:00Z",
        })
        assert resp.status_code == 201, resp.text
        assert resp.json()["userinfo"] == alice["userid"]

    def test_cannot_post_reading_to_other_users_field(self, alice, bob):
        field = _create_field(alice)
        resp = client.post("/moisture/", headers=bob["headers"], json={
            "moisture": 10.0, "deviceid": "evil", "fieldid": field["fieldid"],
            "rtctime": "2026-10-08T10:00:00Z",
        })
        assert resp.status_code == 404

    def test_other_user_gets_404_for_field_moisture(self, alice, bob):
        field = _create_field(alice)
        client.post("/moisture/", headers=alice["headers"], json={
            "moisture": 33.0, "deviceid": "dev-1", "fieldid": field["fieldid"],
            "rtctime": "2026-10-08T10:00:00Z",
        })
        own = client.get(f"/moisture/field/{field['fieldid']}", headers=alice["headers"])
        assert own.status_code == 200 and len(own.json()) == 1
        other = client.get(f"/moisture/field/{field['fieldid']}", headers=bob["headers"])
        assert other.status_code == 404


@pytest.mark.integration
class TestLoginLockout:
    def _login(self, mobileno: str, password: str):
        return client.post("/auth/login", json={"mobileno": mobileno, "password": password})

    def test_lockout_after_max_failures(self, alice):
        for _ in range(settings.login_max_attempts - 1):
            assert self._login(alice["mobileno"], "wrong").status_code == 401
        locked = self._login(alice["mobileno"], "wrong")
        assert locked.status_code == 429
        assert int(locked.headers["Retry-After"]) > 0
        # Even the correct password is refused while locked
        assert self._login(alice["mobileno"], PASSWORD).status_code == 429

    def test_lock_expires(self, alice, db_session):
        for _ in range(settings.login_max_attempts):
            self._login(alice["mobileno"], "wrong")
        assert self._login(alice["mobileno"], PASSWORD).status_code == 429
        # Simulate the lockout window passing
        db_session.execute(
            text("UPDATE appschema.login_attempts SET locked_until = now() - interval '1 second' "
                 "WHERE mobileno = :m"), {"m": alice["mobileno"]})
        db_session.commit()
        assert self._login(alice["mobileno"], PASSWORD).status_code == 200

    def test_success_resets_counter(self, alice):
        for _ in range(settings.login_max_attempts - 1):
            self._login(alice["mobileno"], "wrong")
        assert self._login(alice["mobileno"], PASSWORD).status_code == 200
        # Counter was reset, so another max-1 failures don't lock
        for _ in range(settings.login_max_attempts - 1):
            assert self._login(alice["mobileno"], "wrong").status_code == 401
        assert self._login(alice["mobileno"], PASSWORD).status_code == 200

    def test_unknown_numbers_are_locked_too(self):
        mobileno = _unique_mobile()
        codes = [self._login(mobileno, "x").status_code for _ in range(settings.login_max_attempts)]
        assert codes[:-1] == [401] * (settings.login_max_attempts - 1)
        assert codes[-1] == 429

    def test_unknown_user_timing_similar(self, alice):
        def timed(mobileno):
            start = time.perf_counter()
            self._login(mobileno, "wrong")
            return time.perf_counter() - start

        known = timed(alice["mobileno"])
        unknown = timed(_unique_mobile())
        # Both paths run one bcrypt check; loose bound to stay non-flaky
        assert unknown > known * 0.3
