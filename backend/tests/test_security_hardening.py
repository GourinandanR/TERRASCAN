import os, tempfile
from fastapi.testclient import TestClient

def test_security_headers_and_auth_throttle(monkeypatch):
    fd, db = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    monkeypatch.setenv("TERRASCAN_DB_PATH", db)
    monkeypatch.setenv("TERRASCAN_LOGIN_RATE_LIMIT", "2")
    from app.main import app, _rate_events, _rate_lock
    with _rate_lock:
        _rate_events.clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["referrer-policy"] == "no-referrer"
            assert client.post("/api/auth/login", json={"username":"nobody","password":"wrong-password"}).status_code == 401
            assert client.post("/api/auth/login", json={"username":"nobody","password":"wrong-password"}).status_code == 401
            limited = client.post("/api/auth/login", json={"username":"nobody","password":"wrong-password"})
            assert limited.status_code == 429
            assert limited.headers["retry-after"] == "60"
    finally:
        try: os.unlink(db)
        except OSError: pass
