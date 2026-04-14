#!/usr/bin/env python3
"""Quick test script — send audio file to /transcribe endpoint."""
import base64
import json
import sys
import requests
from pathlib import Path

def test_transcribe(audio_path: str, language: str = "auto"):
    """Send audio file to /transcribe, print response."""
    audio_file = Path(audio_path)
    if not audio_file.exists():
        print(f"❌ File not found: {audio_path}")
        sys.exit(1)

    # Read and base64-encode
    audio_bytes = audio_file.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    print(f"📄 File: {audio_path}")
    print(f"📊 Size: {len(audio_bytes)} bytes")
    print(f"🗣️  Language: {language}")
    print()

    # POST to service
    try:
        resp = requests.post(
            "http://127.0.0.1:8765/transcribe",
            json={"audio_base64": audio_b64, "language": language},
            timeout=60
        )
    except requests.ConnectionError:
        print("❌ Service not running!")
        print("   Start it: cd services/whisper && ./start.sh")
        sys.exit(1)

    # Show response
    if resp.status_code == 200:
        data = resp.json()
        print("✅ Success (200)")
        print(f"   Text: {data['text'][:100]}{'...' if len(data['text']) > 100 else ''}")
        print(f"   Language: {data['language']}")
        print(f"   Duration: {data['duration_s']}s")
        print(f"   Latency: {data['latency_ms']}ms")
        print()
        print("Full response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Error ({resp.status_code})")
        print(json.dumps(resp.json(), indent=2))
        sys.exit(1)

if __name__ == "__main__":
    # Default: Polish sample
    test_transcribe("fixtures/pl_chrzaszcz.ogg", language="pl")
    print(" ");
    test_transcribe("fixtures/pl_smartfon.ogg")
