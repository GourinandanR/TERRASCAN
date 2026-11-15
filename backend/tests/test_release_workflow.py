import os, tempfile
from fastapi.testclient import TestClient

def test_first_admin_login_user_management_and_logout():
    fd, db = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    os.environ["TERRASCAN_DB_PATH"] = db
    from app.main import app
    try:
        with TestClient(app) as client:
            created = client.post("/api/auth/register", json={"username":"release_admin","password":"Strong-Release-Password-9"})
            assert created.status_code == 200, created.text
            admin_token = created.json()["access_token"]
            assert client.get("/api/auth/me", headers={"Authorization":f"Bearer {admin_token}"}).status_code == 200
            user = client.post("/api/auth/users", json={"username":"release_viewer","password":"Viewer-Password-Strong-9","role":"viewer"}, headers={"Authorization":f"Bearer {admin_token}"})
            assert user.status_code == 200, user.text
            assert client.post("/api/auth/login", json={"username":"release_viewer","password":"Viewer-Password-Strong-9"}).status_code == 200
            viewer_token = client.post("/api/auth/login", json={"username":"release_viewer","password":"Viewer-Password-Strong-9"}).json()["access_token"]
            assert client.get("/api/auth/users", headers={"Authorization":f"Bearer {viewer_token}"}).status_code == 403
            assert client.post("/api/auth/logout", headers={"Authorization":f"Bearer {admin_token}"}).status_code == 200
            assert client.get("/api/auth/me", headers={"Authorization":f"Bearer {admin_token}"}).status_code == 401
            assert client.post("/api/auth/register", json={"username":"second_admin","password":"Another-Strong-Password-9"}).status_code == 403
    finally:
        try: os.unlink(db)
        except OSError: pass
