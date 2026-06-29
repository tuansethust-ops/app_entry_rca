import sys
from pathlib import Path
from fastapi.testclient import TestClient
import time
import json

from web.server import app, job_manager

client = TestClient(app)

def test_api():
    print("Testing /")
    response = client.get("/")
    assert response.status_code == 200
    assert "App Entry RCA" in response.text
    
    print("Testing /api/browse")
    response = client.get("/api/browse?path=.")
    assert response.status_code == 200
    assert "items" in response.json()
    
    # We won't test /api/analyze fully since it requires real traces, but we can test invalid paths
    print("Testing /api/analyze with invalid paths")
    response = client.post("/api/analyze", json={
        "dut_path": "invalid1.log",
        "ref_path": "invalid2.log"
    })
    assert response.status_code == 400
    
    print("All API tests passed!")

if __name__ == "__main__":
    test_api()
