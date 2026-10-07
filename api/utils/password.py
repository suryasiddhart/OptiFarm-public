"""Password hashing utilities using passlib."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Check a password; always performs one bcrypt verification.

    When there is no stored hash (unknown user, or an account registered
    without a password) a dummy hash is verified instead, so the response
    time doesn't reveal whether the account exists.
    """
    if not hashed_password:
        pwd_context.verify(plain_password, _DUMMY_HASH)
        return False
    return pwd_context.verify(plain_password, hashed_password)


# Hash of a random value, only used to equalise timing in verify_password()
_DUMMY_HASH = pwd_context.hash("timing-equaliser-not-a-real-password")
