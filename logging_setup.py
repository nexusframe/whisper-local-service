"""JSON logging setup."""
import json
import logging
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
  """Format logs as JSON lines."""

  def format(self, record: logging.LogRecord) -> str:
    """Format log record as JSON with extra fields."""
    log_data = {
      "ts": datetime.utcnow().isoformat() + "Z",
      "level": record.levelname,
      "msg": record.getMessage(),
    }
    if record.exc_info:
      log_data["exc"] = self.formatException(record.exc_info)
    # Capture extra fields (request_id, audio_bytes, language_requested, etc.)
    for key, val in record.__dict__.items():
      if key not in {
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs", "pathname",
        "process", "processName", "relativeCreated", "thread", "threadName",
        "exc_info", "exc_text", "stack_info", "message"
      }:
        log_data[key] = val
    return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> logging.Logger:
  """Configure JSON logging to stdout."""
  logger = logging.getLogger("whisper")
  logger.setLevel(level)
  logger.handlers.clear()

  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(JSONFormatter())
  logger.addHandler(handler)

  return logger
