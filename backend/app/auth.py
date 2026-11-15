import hashlib, hmac, secrets, sqlite3
from datetime import datetime, timedelta, timezone

ITERATIONS = 310_000

def hash_password(password: str):
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt.hex(), digest.hex()

def verify_password(password: str, salt_hex: str, digest_hex: str):
    try:
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return hmac.compare_digest(actual, expected)

def issue_token():
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode("ascii")).hexdigest()

def token_digest(raw: str):
    return hashlib.sha256(raw.encode("ascii")).hexdigest()

def token_expiry(hours=12):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()

def token_is_expired(value):
    try:
        expiry = datetime.fromisoformat(value)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expiry.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return True

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def create_auth_tables(conn: sqlite3.Connection):
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('viewer','analyst','admin')),
        active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS user_sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL,
        revoked_at TEXT, created_at TEXT NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash)")
