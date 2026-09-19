from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app

# These endpoint tests run against the Compose PostgreSQL service after migrations.
client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"

def test_auth_flow():
    payload = {"name":"Test User","email":f"test-{uuid4()}@example.com","password":"password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409
    assert client.post("/api/auth/login", json={"email":payload["email"],"password":"wrong"}).status_code == 401
    token = client.post("/api/auth/login", json={"email":payload["email"],"password":payload["password"]}).json()["access_token"]
    assert client.get("/api/users/me").status_code == 401
    me = client.get("/api/users/me", headers={"Authorization":f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == payload["email"]
