#!/usr/bin/env python3
"""
Pre-flight model validation. Checks if model is cached and loadable.
Exit code 0 = OK, exit code 1 = error.
"""
import sys
from pathlib import Path

def main():
    try:
        # Try to load on CPU (doesn't require GPU)
        from faster_whisper import WhisperModel

        print("Loading model large-v3 on CPU (validation mode)...", file=sys.stderr)
        model = WhisperModel("large-v3", device="cpu", compute_type="float32")
        print("✓ Model large-v3 loaded successfully", file=sys.stderr)
        return 0

    except FileNotFoundError as e:
        print(f"✗ Model not found in cache: {e}", file=sys.stderr)
        print("Run './setup.sh' to download the model.", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"✗ Model validation failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
