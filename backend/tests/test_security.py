import os
from fastapi.testclient import TestClient
from app.main import app

READ_KEY = "r" * 64
ADMIN_KEY = "a" * 64

def test_authentication_disabled_for_local_dev(monkeypatch):
    monkeypatch.setenv("TERRASCAN_AUTH_REQUIRED", "false")
    monkeypatch.delenv("TERRASCAN_API_KEYS", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/manifests").status_code == 200

def test_authentication_rejects_missing_and_invalid_keys(monkeypatch):
    monkeypatch.setenv("TERRASCAN_AUTH_REQUIRED", "true")
    monkeypatch.setenv("TERRASCAN_API_KEYS", f"{READ_KEY}:read,{ADMIN_KEY}:admin")
    with TestClient(app) as client:
        assert client.get("/api/manifests").status_code == 401
        assert client.get("/api/manifests", headers={"Authorization": "Bearer " + "x" * 64}).status_code == 401

def test_read_key_cannot_write_but_admin_can(monkeypatch):
    monkeypatch.setenv("TERRASCAN_AUTH_REQUIRED", "true")
    monkeypatch.setenv("TERRASCAN_API_KEYS", f"{READ_KEY}:read,{ADMIN_KEY}:admin")
    payload = {"dataset_id":"security-test","version":"1","sha256":"e"*64,"source_uri":"https://example.org/security"}
    with TestClient(app) as client:
        assert client.get("/api/manifests", headers={"Authorization": f"Bearer {READ_KEY}"}).status_code == 200
        assert client.post("/api/manifests", json=payload, headers={"Authorization": f"Bearer {READ_KEY}"}).status_code == 403
        assert client.post("/api/manifests", json=payload, headers={"Authorization": f"Bearer {ADMIN_KEY}"}).status_code == 201

def test_health_probes_remain_public(monkeypatch):
    monkeypatch.setenv("TERRASCAN_AUTH_REQUIRED", "true")
    monkeypatch.delenv("TERRASCAN_API_KEYS", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/ready").status_code == 200

def test_auth_enabled_without_keys_fails_closed(monkeypatch):
    monkeypatch.setenv("TERRASCAN_AUTH_REQUIRED", "true")
    monkeypatch.delenv("TERRASCAN_API_KEYS", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/manifests").status_code == 503
