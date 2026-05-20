import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("AUTOMX2_URL", "http://example.com")


def test_root_returns_ok():
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"
