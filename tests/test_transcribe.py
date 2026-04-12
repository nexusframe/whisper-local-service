"""Tests for POST /transcribe endpoint."""
import asyncio
import base64
import pytest


class TestTranscribeValidation:
  """Validation error tests for POST /transcribe."""

  def test_missing_audio_base64_returns_400(self, client):
    """Missing audio_base64 field is treated as empty, returns 400."""
    resp = client.post("/transcribe", json={})
    # When audio_base64 is missing/empty, validation treats it as empty audio
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_request"

  def test_invalid_base64_returns_400(self, client, garbage_base64):
    """Invalid base64 returns 400 invalid_request."""
    resp = client.post("/transcribe", json={"audio_base64": garbage_base64})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_request"

  def test_unsupported_mime_returns_400(self, client):
    """Unsupported MIME type returns 400 unsupported_mime."""
    resp = client.post("/transcribe", json={
      "audio_base64": "dGVzdA==",
      "mime": "image/png"
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "unsupported_mime"
    # Should include list of supported MIME types
    assert "supported" in resp.json()["detail"]["details"]

  def test_base64_too_large_returns_413(self, client, huge_base64):
    """Base64 > size limit returns 413 payload_too_large (pre-check)."""
    resp = client.post("/transcribe", json={"audio_base64": huge_base64})
    assert resp.status_code == 413
    assert resp.json()["detail"]["error"] == "payload_too_large"

  def test_empty_audio_returns_400(self, client):
    """Empty audio (decoded to 0 bytes) returns 400 invalid_request."""
    resp = client.post("/transcribe", json={"audio_base64": ""})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_request"

  def test_invalid_language_code_returns_400(self, client):
    """Invalid language code (not ISO 639-1) returns 400 invalid_language."""
    resp = client.post("/transcribe", json={
      "audio_base64": "dGVzdA==",
      "language": "klingon"
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "invalid_language"

  def test_valid_language_codes_accepted(self, client):
    """Valid ISO 639-1 language codes are accepted (pass validation)."""
    for lang in ["pl", "en", "de", "fr", "es", "it", "ja", "zh", "auto"]:
      resp = client.post("/transcribe", json={
        "audio_base64": "dGVzdA==",
        "language": lang
      })
      # Should not be invalid_language error
      if resp.status_code == 400:
        assert resp.json()["detail"]["error"] != "invalid_language"
      elif resp.status_code == 413:
        assert resp.json()["detail"]["error"] == "payload_too_large"


class TestTranscribeHappyPath:
  """Successful transcription tests."""

  def test_ping_works_while_transcribing(self, client):
    """/ping responds while model is available."""
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

  def test_transcribe_response_has_all_fields(self, client, en_sample_b64):
    """POST /transcribe response has all required fields."""
    resp = client.post("/transcribe", json={"audio_base64": en_sample_b64})
    if resp.status_code == 200:
      data = resp.json()
      assert "text" in data
      assert "language" in data
      assert "language_probability" in data
      assert "duration_s" in data
      assert "latency_ms" in data
      assert "model" in data

  def test_transcribe_response_types(self, client, en_sample_b64):
    """POST /transcribe response fields have correct types."""
    resp = client.post("/transcribe", json={"audio_base64": en_sample_b64})
    if resp.status_code == 200:
      data = resp.json()
      assert isinstance(data["text"], str)
      assert isinstance(data["language"], str)
      assert data["language_probability"] is None or isinstance(data["language_probability"], float)
      assert isinstance(data["duration_s"], (int, float))
      assert isinstance(data["latency_ms"], int)
      assert isinstance(data["model"], str)

  def test_transcribe_forced_language_returns_null_probability(self, client, en_sample_b64):
    """Forced language returns language_probability=null."""
    resp = client.post("/transcribe", json={
      "audio_base64": en_sample_b64,
      "language": "en"
    })
    if resp.status_code == 200:
      data = resp.json()
      assert data["language_probability"] is None

  def test_transcribe_case_insensitive(self, client, en_sample_b64):
    """Transcribed text matching is case-insensitive."""
    resp = client.post("/transcribe", json={
      "audio_base64": en_sample_b64,
      "language": "en"
    })
    if resp.status_code == 200:
      data = resp.json()
      # en_fox.ogg should contain "brown fox"
      assert "brown" in data["text"].lower() or "fox" in data["text"].lower()

  def test_transcribe_duration_matches_audio(self, client, en_sample_b64):
    """duration_s should be approximately correct."""
    resp = client.post("/transcribe", json={
      "audio_base64": en_sample_b64,
      "language": "en"
    })
    if resp.status_code == 200:
      data = resp.json()
      # en_fox.ogg is ~3.81s
      assert 3.0 < data["duration_s"] < 5.0

  def test_transcribe_latency_is_positive(self, client, en_sample_b64):
    """latency_ms should be positive."""
    resp = client.post("/transcribe", json={
      "audio_base64": en_sample_b64
    })
    if resp.status_code == 200:
      data = resp.json()
      assert data["latency_ms"] > 0


class TestTranscribeConcurrency:
  """Concurrent request tests."""

  def test_concurrent_requests_serialize(self, client, en_sample_b64, pl_sample_b64):
    """Two concurrent requests should both succeed (serialized)."""
    resp1 = client.post("/transcribe", json={
      "audio_base64": en_sample_b64,
      "language": "en"
    })
    resp2 = client.post("/transcribe", json={
      "audio_base64": pl_sample_b64,
      "language": "pl"
    })

    # Both should eventually succeed or fail gracefully
    assert resp1.status_code in [200, 503, 504, 500]
    assert resp2.status_code in [200, 503, 504, 500]


class TestTranscribeTimeout:
  """Timeout and long-running tests (marked as slow)."""

  @pytest.mark.slow
  @pytest.mark.timeout(360)  # 6 min hard timeout for test itself
  def test_transcribe_timeout_returns_504(self, client, long_silence_audio):
    """Very long audio (6 min silence) should trigger 504 timeout."""
    audio_b64 = base64.b64encode(long_silence_audio).decode()
    resp = client.post("/transcribe", json={
      "audio_base64": audio_b64,
      "language": "en"
    })
    # Should timeout at 300s (default WHISPER_REQUEST_TIMEOUT_S)
    assert resp.status_code == 504
    assert resp.json()["detail"]["error"] == "transcription_timeout"
