"""Pytest fixtures and configuration."""
from pathlib import Path
import base64
import io

import pytest
import numpy as np
from fastapi.testclient import TestClient

from server import app


@pytest.fixture(scope="session")
def client():
  """FastAPI test client (triggers lifespan)."""
  with TestClient(app) as c:
    yield c


@pytest.fixture(scope="session")
def fixtures_dir():
  """Path to test audio fixtures."""
  return Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def pl_sample(fixtures_dir):
  """Polish sample: pl_chrzaszcz.ogg (9.21s, tongue twister)."""
  return (fixtures_dir / "pl_chrzaszcz.ogg").read_bytes()


@pytest.fixture(scope="session")
def pl_sample_b64(pl_sample):
  """Polish sample as base64."""
  return base64.b64encode(pl_sample).decode()


@pytest.fixture(scope="session")
def en_sample(fixtures_dir):
  """English sample: en_fox.ogg (3.81s, pangram)."""
  return (fixtures_dir / "en_fox.ogg").read_bytes()


@pytest.fixture(scope="session")
def en_sample_b64(en_sample):
  """English sample as base64."""
  return base64.b64encode(en_sample).decode()


@pytest.fixture(scope="session")
def pl_alphabet_sample(fixtures_dir):
  """Polish alphabet: pl_alphabet.ogg (29.22s, diacritics stress)."""
  path = fixtures_dir / "pl_alphabet.ogg"
  if path.exists():
    return path.read_bytes()
  return None


@pytest.fixture(scope="session")
def pl_smartfon_sample(fixtures_dir):
  """Polish long-form: pl_smartfon.ogg (39.45s, natural reading)."""
  path = fixtures_dir / "pl_smartfon.ogg"
  if path.exists():
    return path.read_bytes()
  return None


@pytest.fixture(scope="session")
def en_uk_north_wind_sample(fixtures_dir):
  """English long-form: en_uk_north_wind.ogg (36.43s, UK RP)."""
  path = fixtures_dir / "en_uk_north_wind.ogg"
  if path.exists():
    return path.read_bytes()
  return None


@pytest.fixture(scope="session")
def en_us_election_sample(fixtures_dir):
  """English US: en_us_election.ogg (8s, legal vocab)."""
  path = fixtures_dir / "en_us_election.ogg"
  if path.exists():
    return path.read_bytes()
  return None


@pytest.fixture
def empty_audio():
  """Empty audio bytes."""
  return b""


@pytest.fixture
def garbage_base64():
  """Invalid base64 string."""
  return "not-valid-base64!!!"


@pytest.fixture
def huge_base64():
  """Base64 string exceeding size limit (~35 MB)."""
  # 35 MB of 'A's in base64 (size limit is ~33 MB)
  return "A" * (35 * 1024 * 1024)


@pytest.fixture
def long_silence_audio():
  """6 minute silence for timeout testing.

  5,760,000 samples at 16 kHz = 360 seconds = 6 minutes.
  This should trigger WHISPER_REQUEST_TIMEOUT_S (default 300s).
  """
  samples = np.zeros(5_760_000, dtype=np.float32)
  bio = io.BytesIO()
  try:
    import soundfile
    soundfile.write(bio, samples, 16000, format='WAV')
    return bio.getvalue()
  except ImportError:
    # Fallback: create minimal WAV without soundfile
    # 44 byte WAV header + silence
    import struct
    sample_rate = 16000
    num_samples = 5_760_000

    # WAV header
    channels = 1
    sample_width = 2
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    data_size = num_samples * channels * sample_width

    wav = io.BytesIO()
    # RIFF header
    wav.write(b'RIFF')
    wav.write(struct.pack('<I', 36 + data_size))
    wav.write(b'WAVE')
    # fmt subchunk
    wav.write(b'fmt ')
    wav.write(struct.pack('<I', 16))
    wav.write(struct.pack('<HHIIHH', 1, channels, sample_rate, byte_rate, block_align, 16))
    # data subchunk
    wav.write(b'data')
    wav.write(struct.pack('<I', data_size))
    wav.write(b'\x00' * data_size)

    return wav.getvalue()


@pytest.fixture
def marker(request):
  """Mark slow tests."""
  return request.node.get_closest_marker("slow")
