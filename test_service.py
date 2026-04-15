#!/usr/bin/env python3
"""Quick test script — send audio file to /transcribe endpoint."""
import base64
import json
import sys
import requests
from pathlib import Path

def test_transcribe(
    audio_path: str,
    language: str = "auto",
    timestamps: bool = False,
    initial_prompt: str = None
):
    """Send audio file to /transcribe, print response."""
    audio_file = Path(audio_path)
    if not audio_file.exists():
        print(f"File not found: {audio_path}")
        sys.exit(1)

    audio_bytes = audio_file.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    print(f"File: {audio_path}")
    print(f"Size: {len(audio_bytes)} bytes")
    print(f"Language: {language}")
    if initial_prompt:
        print(f"Prompt: {initial_prompt}")
    if timestamps:
        print(f"Timestamps: on")
    print()

    payload = {"audio_base64": audio_b64, "language": language, "timestamps": timestamps}
    if initial_prompt:
        payload["initial_prompt"] = initial_prompt

    try:
        resp = requests.post(
            "http://127.0.0.1:8765/transcribe",
            json=payload,
            timeout=60
        )
    except requests.ConnectionError:
        print("Service not running! Start it: cd services/whisper && ./start.sh")
        sys.exit(1)

    if resp.status_code == 200:
        data = resp.json()
        print(f"OK (200) | {data['duration_s']}s | {data['latency_ms']}ms | {data['language']}")
        print(f"Text: {data['text'][:200]}{'...' if len(data['text']) > 200 else ''}")
        if data.get("segments"):
            print(f"Segments ({len(data['segments'])}):")
            for s in data["segments"]:
                print(f"  [{s['start']:6.2f} - {s['end']:6.2f}] {s['text']}")
        print()
    else:
        print(f"Error ({resp.status_code})")
        print(json.dumps(resp.json(), indent=2))
        sys.exit(1)

if __name__ == "__main__":
    test_transcribe("fixtures/pl_chrzaszcz.ogg", language="pl", timestamps=True)
    test_transcribe("fixtures/pl_smartfon.ogg", timestamps=True)
