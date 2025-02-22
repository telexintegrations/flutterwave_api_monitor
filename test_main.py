import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)

mock_status_response = {
    "status": {
        "description": "All systems operational",
        "indicator": "none"
    },
    "page": {
        "updated_at": "2025-02-20T10:00:00Z"
    }
}

@pytest.fixture
def mock_httpx_get():
    with patch("httpx.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_status_response
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        yield mock_post


def test_fetch_status_api(mock_httpx_get):
    """Test the root endpoint that fetches Flutterwave API status"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "All systems operational",
        "indicator": "none",
        "updated_at": "2025-02-20T10:00:00Z"
    }


def test_send_incident_update(mock_httpx_post):
    """Test the tick endpoint that triggers background task"""
    response = client.post("/tick")
    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted",
        "message": "Incident update is being processed"
    }


def test_get_integration():
    """Test fetching integration.json file"""
    response = client.get("/integration")
    assert response.status_code == 200
    
    with open("integration.json", "r") as file:
        expected_data = json.load(file)

    assert response.json() == expected_data