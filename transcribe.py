"""WhisperExecutor — model loading and transcription."""
import asyncio
import io
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from logging_setup import setup_logging

logger = setup_logging()


class WhisperExecutor:
  """Manages Whisper model lifecycle and transcription calls.

  Uses ThreadPoolExecutor to serialize transcribe() calls, avoiding event
  loop blocking from sync faster-whisper code.
  """

  def __init__(self, model_name: str = "large-v3", compute_type: str = "auto", device: str = "auto"):
    """Initialize executor with model name, compute type, and device.

    Args:
      model_name: Whisper model (e.g., "large-v3")
      compute_type: Quantization ("auto", "int8", "float32", etc.)
      device: "auto", "cuda", or "cpu"
    """
    self.model_name = model_name
    self.compute_type = compute_type
    self.device = device
    self.model: Optional[WhisperModel] = None
    self.executor = ThreadPoolExecutor(max_workers=1)
    self.warmup_complete = False
    self.startup_time: Optional[float] = None

  async def startup(self) -> None:
    """Load model and run warmup."""
    start = time.time()
    logger.info(f"Loading model {self.model_name} on {self.device}...")

    # Load model (blocking)
    self.model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
    load_ms = int((time.time() - start) * 1000)
    logger.info(f"Model loaded", extra={"latency_ms": load_ms})

    # Warmup with 30s timeout
    try:
      warmup_start = time.time()
      loop = asyncio.get_event_loop()
      await asyncio.wait_for(
        loop.run_in_executor(self.executor, self._warmup),
        timeout=30
      )
      warmup_ms = int((time.time() - warmup_start) * 1000)
      logger.info(f"Warmup complete", extra={"latency_ms": warmup_ms})
      self.warmup_complete = True
    except asyncio.TimeoutError:
      logger.warning("Warmup timeout (>30s)", extra={"warmup_complete": False})
      self.warmup_complete = False
    except Exception as e:
      logger.warning(f"Warmup failed: {e}", extra={"warmup_complete": False})
      self.warmup_complete = False

    self.startup_time = time.time()

  async def shutdown(self) -> None:
    """Cleanup executor."""
    self.executor.shutdown(wait=True)

  def _warmup(self) -> None:
    """Synchronous warmup: transcribe 2s silence."""
    silence = np.zeros(32000, dtype=np.float32)
    self.model.transcribe(silence, vad_filter=False, language="en")

  async def transcribe(
    self,
    audio_bytes: bytes,
    language: str = "auto",
    timeout_s: int = 300
  ) -> dict:
    """
    Transcribe audio. Returns dict with text, language, probability, duration, latency, model.
    """
    start = time.time()
    loop = asyncio.get_event_loop()
    result = await asyncio.wait_for(
      loop.run_in_executor(self.executor, self._do_transcribe, audio_bytes, language),
      timeout=timeout_s
    )
    return result

  def _do_transcribe(self, audio_bytes: bytes, language: str) -> dict:
    """
    Synchronous transcription (runs in executor).

    NOTE: model.transcribe() returns a lazy generator for segments.
    Must call list() to materialize and trigger actual inference.
    """
    start = time.time()
    bio = io.BytesIO(audio_bytes)

    segments, info = self.model.transcribe(
      bio,
      language=None if language == "auto" else language,
      vad_filter=True
    )

    # Materialize generator — inference actually runs here
    segments_list = list(segments)
    latency_ms = int((time.time() - start) * 1000)

    # Join segments and clean whitespace
    text = " ".join(s.text.strip() for s in segments_list).strip()
    duration = info.duration

    # Language detection logic
    if info.language is None:
      # Silent audio, model couldn't detect
      detected_lang = "unknown"
      lang_prob = None
    elif language != "auto":
      # Explicit language forced, no detection
      detected_lang = info.language
      lang_prob = None
    else:
      # Auto-detect mode
      detected_lang = info.language
      lang_prob = info.language_probability

    return {
      "text": text,
      "language": detected_lang,
      "language_probability": lang_prob,
      "duration_s": round(duration, 2),
      "latency_ms": latency_ms,
      "model": self.model_name,
    }
