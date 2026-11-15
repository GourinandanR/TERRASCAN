from fastapi.testclient import TestClient
from app.main import app

def test_liveness_endpoint():
    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'
        assert response.json()['version'] == '3.1.0'

def test_readiness_endpoint():
    with TestClient(app) as client:
        response = client.get('/api/ready')
        assert response.status_code == 200
        assert response.json()['status'] == 'ready'
        assert response.json()['database'] == 'connected'
