"""Pydantic schemas for request/response."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# Supported MIME types (from api_spec.md)
SUPPORTED_MIMES = {
  "audio/mpeg", "audio/mp3",
  "audio/wav", "audio/x-wav",
  "audio/ogg", "audio/opus",
  "audio/flac",
  "audio/webm",
  "audio/m4a"
}


class TranscribeRequest(BaseModel):
  """Request body for POST /transcribe endpoint.

  Accepts audio in base64 format with optional MIME type and language.
  Language defaults to auto-detection.
  """
  audio_base64: str = Field(..., description="Base64-encoded audio bytes")
  mime: Optional[str] = Field(
    None, description="MIME type (audio/mpeg, audio/wav, audio/ogg, etc.)"
  )
  language: Optional[str] = Field(
    "auto", description="ISO 639-1 code (pl, en, de, ...) or 'auto'"
  )

  @field_validator("language")
  @classmethod
  def validate_language(cls, v: str) -> str:
    """Validate language code is ISO 639-1 or 'auto'."""
    if v == "auto":
      return v
    valid_codes = {
      "af", "ar", "hy", "az", "be", "bs", "bg", "ca", "ceb", "zh", "cv",
      "cy", "da", "nl", "en", "et", "tl", "fi", "fr", "gl", "ka", "de",
      "el", "gu", "ht", "ha", "haw", "he", "hi", "hu", "is", "ig", "id",
      "ga", "it", "ja", "jv", "kn", "kk", "km", "ko", "ku", "ky", "lo",
      "la", "lv", "lt", "lb", "mk", "mg", "ms", "ml", "mt", "mi", "mr",
      "mn", "my", "ne", "no", "oc", "ps", "fa", "pl", "pt", "pa", "ro",
      "ru", "sm", "sr", "sk", "sl", "so", "es", "su", "sw", "sv", "tg",
      "ta", "te", "th", "tr", "tk", "uk", "ur", "ug", "uz", "vi", "cy",
      "xh", "yi", "yo", "zu"
    }
    if v.lower() not in valid_codes:
      raise ValueError(f"Invalid language code: {v}")
    return v.lower()


class TranscribeResponse(BaseModel):
  """Response body for POST /transcribe (200 OK)."""
  text: str
  language: str
  language_probability: Optional[float] = None
  duration_s: float
  latency_ms: int
  model: str


class HealthResponse(BaseModel):
  """Response body for GET /health."""
  model_loaded: bool
  warmup_complete: bool
  model_name: str
  device: str
  compute_type: str
  uptime_s: int


class ErrorResponse(BaseModel):
  """Error response body (4xx, 5xx)."""
  error: str
  message: str
  details: dict = {}
