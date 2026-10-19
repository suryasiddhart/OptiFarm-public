"""Device passkey generation and hashing.

Hashes use the same scheme as Mosquitto's dynamic-security plugin
("$7$<iterations>$<salt_b64>$<hash_b64>": PBKDF2-HMAC-SHA512, 64-byte salt,
64-byte hash), so ingest/dynsec_sync.py can write them straight into the
broker config and Mosquitto verifies device logins against them.
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

# Mosquitto's own default. Passkeys are 256-bit random tokens, so a higher
# work factor would only add CPU cost to every device connect.
PASSKEY_ITERATIONS = 1000
_SALT_BYTES = 64
_HASH_BYTES = 64


@dataclass(frozen=True)
class PasskeyHash:
    hash: str        # base64
    salt: str        # base64
    iterations: int


def generate_passkey() -> str:
    return secrets.token_urlsafe(32)


def hash_passkey(passkey: str, salt: bytes | None = None,
                 iterations: int = PASSKEY_ITERATIONS) -> PasskeyHash:
    salt = salt if salt is not None else secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha512", passkey.encode(), salt, iterations, _HASH_BYTES)
    return PasskeyHash(
        hash=base64.b64encode(digest).decode(),
        salt=base64.b64encode(salt).decode(),
        iterations=iterations,
    )


def verify_passkey(passkey: str, stored: PasskeyHash) -> bool:
    candidate = hash_passkey(passkey, base64.b64decode(stored.salt), stored.iterations)
    return hmac.compare_digest(candidate.hash, stored.hash)


def to_mosquitto_encoded(stored: PasskeyHash) -> str:
    """The dynamic-security.json `encoded_password` value."""
    return f"$7${stored.iterations}${stored.salt}${stored.hash}"
