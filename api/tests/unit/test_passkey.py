"""Unit tests for device passkey hashing (Mosquitto dynamic-security format)."""

import pytest

from utils.passkey import (
    PasskeyHash,
    generate_passkey,
    hash_passkey,
    to_mosquitto_encoded,
    verify_passkey,
)

# Written by Mosquitto 2.1.2 itself (`mosquitto_ctrl dynsec init ... admin AdminPass123`)
MOSQUITTO_ENCODED = (
    "$7$1000$pv2laY0qGsO7Fk8SUwIGOvQ6cd7BBM7/BaEYBTHf9xczuHLF0b6S40Ep90WkNZx6E3rBigRMUgd2BjsW8r6bMg=="
    "$JnBZvCaeMwhjCQu2iF2RO5a3qRsIIobaG2/HyYHrHIcrNQZvNTLSOfPljBhSF/BNpl7IqvYYbAv0ryzpDBtS9A=="
)


def _parse(encoded: str) -> PasskeyHash:
    _, version, iterations, salt, digest = encoded.split("$")
    assert version == "7"
    return PasskeyHash(hash=digest, salt=salt, iterations=int(iterations))


@pytest.mark.unit
class TestPasskey:
    def test_verifies_hash_written_by_mosquitto(self):
        stored = _parse(MOSQUITTO_ENCODED)
        assert verify_passkey("AdminPass123", stored) is True
        assert verify_passkey("AdminPass124", stored) is False

    def test_round_trip_through_mosquitto_format(self):
        stored = hash_passkey("device-secret")
        assert _parse(to_mosquitto_encoded(stored)) == stored
        assert verify_passkey("device-secret", stored) is True

    def test_salt_is_random(self):
        assert hash_passkey("same").hash != hash_passkey("same").hash

    def test_generated_passkeys_are_unique_and_long(self):
        keys = {generate_passkey() for _ in range(50)}
        assert len(keys) == 50
        assert all(len(k) >= 40 for k in keys)
