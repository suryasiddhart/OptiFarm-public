"""Unit tests for password hashing helpers."""

import pytest

from utils.password import hash_password, verify_password


@pytest.mark.unit
class TestVerifyPassword:
    def test_correct_password(self):
        assert verify_password("s3cret", hash_password("s3cret")) is True

    def test_wrong_password(self):
        assert verify_password("nope", hash_password("s3cret")) is False

    @pytest.mark.parametrize("stored", [None, ""])
    def test_missing_hash_is_rejected(self, stored):
        # Unknown user / account without a password: never authenticates
        assert verify_password("anything", stored) is False
