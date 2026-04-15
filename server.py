"""FastAPI server with background model loading and logging."""
import asyncio
import os
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from logging_setup import setup_logging
from models import ErrorResponse, HealthResponse, TranscribeResponse
from transcribe import WhisperExecutor
from validation import ValidationError, validate_and_decode_audio

logger = setup_logging(level=os.getenv("WHISPER_LOG_LEVEL", "INFO"))

executor: WhisperExecutor = None
startup_timestamp: float = None

app = FastAPI(
  title="Whisper Service",
  description="Local STT microservice"
)


async def load_model_background():
  """Background task to load model."""
  global executor
  try:
    model_name = os.getenv("WHISPER_MODEL", "large-v3")
    executor = WhisperExecutor(
      model_name=model_name,
      device=os.getenv("WHISPER_DEVICE", "auto"),
      compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "auto"),
    )
    await executor.startup()
    logger.info("Whisper service ready", extra={"model": model_name})
  except Exception as e:
    logger.error(f"Failed to load model: {e}")
    executor = None


@app.on_event("startup")
async def startup_event():
  """Start model loading in background."""
  global startup_timestamp
  startup_timestamp = time.time()
  asyncio.create_task(load_model_background())


@app.on_event("shutdown")
async def shutdown_event():
  """Cleanup."""
  if executor:
    await executor.shutdown()


@app.get("/ping", tags=["health"])
async def ping():
  """Lightweight service status (no model required)."""
  return {"status": "ok"}


@app.get("/health", tags=["health"])
async def health():
  """Full service readiness check."""
  if executor is None or not executor.model:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail=ErrorResponse(
        error="model_not_loaded",
        message="Model is still loading",
        details={}
      ).model_dump()
    )

  uptime_s = int(time.time() - startup_timestamp)
  return HealthResponse(
    model_loaded=True,
    warmup_complete=executor.warmup_complete,
    model_name=executor.model_name,
    device=executor.device,
    compute_type=executor.compute_type,
    uptime_s=uptime_s
  )


@app.post("/transcribe", tags=["transcription"])
async def transcribe(request: dict):
  """Transcribe audio (base64)."""
  request_id = uuid4().hex[:12]

  # Check model loaded
  if executor is None or not executor.model:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail=ErrorResponse(
        error="model_not_loaded",
        message="Model not loaded",
        details={}
      ).model_dump()
    )

  # Validate and decode
  try:
    audio_bytes, language = validate_and_decode_audio(
      audio_base64=request.get("audio_base64", ""),
      mime=request.get("mime"),
      language=request.get("language", "auto")
    )
  except ValidationError as e:
    raise HTTPException(
      status_code=e.status_code,
      detail=ErrorResponse(
        error=e.error,
        message=e.message,
        details=e.details
      ).model_dump()
    )

  # Log transcribe start
  logger.info("transcribe_start", extra={
    "request_id": request_id,
    "audio_bytes": len(audio_bytes),
    "language_requested": language
  })

  # Transcribe with timeout
  timeout_s = int(os.getenv("WHISPER_REQUEST_TIMEOUT_S", "300"))
  try:
    result = await executor.transcribe(
      audio_bytes, language, timeout_s=timeout_s,
      initial_prompt=request.get("initial_prompt"),
      timestamps=request.get("timestamps", False)
    )
    # Log transcribe complete
    logger.info("transcribe_complete", extra={
      "request_id": request_id,
      "latency_ms": result["latency_ms"],
      "language_detected": result["language"],
      "duration_s": result["duration_s"]
    })
    return TranscribeResponse(**result)
  except asyncio.TimeoutError:
    raise HTTPException(
      status_code=status.HTTP_504_GATEWAY_TIMEOUT,
      detail=ErrorResponse(
        error="transcription_timeout",
        message=f"Transcription exceeded {timeout_s}s timeout",
        details={}
      ).model_dump()
    )
  except Exception as e:
    logger.error(f"Transcription failed: {e}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=ErrorResponse(
        error="transcription_failed",
        message=str(e),
        details={}
      ).model_dump()
    )
