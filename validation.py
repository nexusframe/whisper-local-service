"""Request validation helpers."""
import base64
import binascii
import os
from typing import Tuple

# ISO 639-1 language codes
ISO_639_1_CODES = {
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


class ValidationError(Exception):
  """Raised when validation fails."""
  def __init__(self, status_code: int, error: str, message: str, details: dict = None):
    self.status_code = status_code
    self.error = error
    self.message = message
    self.details = details or {}
    super().__init__(message)


def validate_and_decode_audio(
  audio_base64: str,
  mime: str = None,
  language: str = "auto"
) -> Tuple[bytes, str]:
  """
  Validate request and decode audio. Returns (audio_bytes, language).
  Raises ValidationError on any validation failure.
  """
  # Check MIME
  if mime:
    from models import SUPPORTED_MIMES
    if mime not in SUPPORTED_MIMES:
      raise ValidationError(
        status_code=400,
        error="unsupported_mime",
        message=f"MIME type '{mime}' not supported",
        details={"supported": list(SUPPORTED_MIMES)}
      )

  # Pre-check base64 size
  max_b64_bytes = int(os.getenv("WHISPER_MAX_BYTES", "26214400")) * 4 / 3
  if len(audio_base64) > max_b64_bytes:
    raise ValidationError(
      status_code=413,
      error="payload_too_large",
      message=f"Audio base64 exceeds {int(max_b64_bytes)} bytes"
    )

  # Decode base64
  try:
    audio_bytes = base64.b64decode(audio_base64)
  except (binascii.Error, ValueError) as e:
    raise ValidationError(
      status_code=400,
      error="invalid_request",
      message=f"Invalid base64: {str(e)}"
    )

  # Validate language code
  lang = language.lower() if language else "auto"
  if lang != "auto" and lang not in ISO_639_1_CODES:
    raise ValidationError(
      status_code=400,
      error="invalid_language",
      message=f"'{language}' is not a valid ISO 639-1 code"
    )

  # Check audio non-empty
  if len(audio_bytes) == 0:
    raise ValidationError(
      status_code=400,
      error="invalid_request",
      message="Audio is empty"
    )

  # Check audio size
  max_bytes = int(os.getenv("WHISPER_MAX_BYTES", "26214400"))
  if len(audio_bytes) > max_bytes:
    raise ValidationError(
      status_code=413,
      error="payload_too_large",
      message=f"Audio exceeds {max_bytes} bytes"
    )

  return audio_bytes, lang
