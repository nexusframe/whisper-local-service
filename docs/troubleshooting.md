# Troubleshooting

## CUDA not found — device shows "cpu"

**Symptom:** Logs show `"device": "cpu"`, transcription very slow (30s+/min audio)

**Fix:**
- Install NVIDIA driver: `nvidia-smi` should show your GPU
- Or accept CPU mode (slow but works)

## cuDNN missing — `libcudnn.so.8: cannot open shared object file`

**Symptom:** Warning during startup, transcription slower than expected

**Fix (Ubuntu):**
```bash
sudo apt update && sudo apt install libcudnn9
```

Or set library path for custom cuDNN install:
```bash
export LD_LIBRARY_PATH=/path/to/cudnn/lib:$LD_LIBRARY_PATH
./start.sh
```

## CUDA Out of Memory (OOM)

**Symptom:** Error during warmup: `CUDA out of memory`

**Fix:**
1. Check if another process uses GPU: `nvidia-smi`
2. If GPU is free but OOM, use smaller model:
   ```bash
   WHISPER_MODEL=large-v3-turbo ./start.sh
   ```
3. Last resort — CPU:
   ```bash
   WHISPER_DEVICE=cpu ./start.sh
   ```

## Port 8765 already in use

**Fix:**
```bash
lsof -i :8765           # Find process
kill <PID>              # Kill it
./start.sh              # Restart
```

Or use a different port:
```bash
WHISPER_PORT=8766 ./start.sh
```

## Model download fails or hangs

**Fix:**
```bash
HF_ENDPOINT=https://huggingface.co ./setup.sh
```

## First request is slow

Normal. First request after startup takes 2-3x longer (GPU kernel compilation). Wait for `"Whisper service ready"` log before sending requests.
