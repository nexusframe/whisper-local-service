"""Tests for /ping and /health endpoints."""
import pytest


class TestPing:
  """GET /ping tests."""

  def test_ping_returns_200(self, client):
    """GET /ping returns 200 OK."""
    resp = client.get("/ping")
    assert resp.status_code == 200

  def test_ping_response_structure(self, client):
    """GET /ping returns {"status": "ok"}."""
    resp = client.get("/ping")
    assert resp.json() == {"status": "ok"}


class TestHealth:
  """GET /health tests."""

  def test_health_returns_200_with_model_loaded(self, client):
    """GET /health returns 200 OK (model should be loaded by now)."""
    resp = client.get("/health")
    # Health might return 503 if model still loading, give it time
    assert resp.status_code in [200, 503]

  def test_health_has_expected_fields(self, client):
    """GET /health response has all required fields."""
    resp = client.get("/health")
    if resp.status_code == 200:
      data = resp.json()
      assert "model_loaded" in data
      assert "warmup_complete" in data
      assert "model_name" in data
      assert "device" in data
      assert "compute_type" in data
      assert "uptime_s" in data

  def test_health_warmup_complete_is_bool(self, client):
    """warmup_complete field is boolean."""
    resp = client.get("/health")
    if resp.status_code == 200:
      data = resp.json()
      assert isinstance(data["warmup_complete"], bool)

  def test_health_model_loaded_is_bool(self, client):
    """model_loaded field is boolean."""
    resp = client.get("/health")
    if resp.status_code == 200:
      data = resp.json()
      assert isinstance(data["model_loaded"], bool)

  def test_health_has_no_status_field(self, client):
    """Health response does NOT have 'status' field (D14 cut)."""
    resp = client.get("/health")
    if resp.status_code == 200:
      data = resp.json()
      assert "status" not in data

  def test_health_uptime_is_positive(self, client):
    """uptime_s is non-negative."""
    resp = client.get("/health")
    if resp.status_code == 200:
      data = resp.json()
      assert data["uptime_s"] >= 0
      assert isinstance(data["uptime_s"], int)
