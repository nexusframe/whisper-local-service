#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "  Whisper Service Setup"
echo "================================================"
echo

# 1. Check Python version
echo -n "Checking Python version... "
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
  echo -e "${RED}✗ Python 3.10+ required (found $PYTHON_VERSION)${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# 2. Create venv
echo -n "Creating virtual environment... "
python3 -m venv .venv
echo -e "${GREEN}✓${NC}"

# 3. Install dependencies
echo -n "Installing dependencies... "
source .venv/bin/activate
pip install --quiet -r requirements.txt
echo -e "${GREEN}✓${NC}"

# 4. Check CUDA (now torch is available)
echo -n "Checking CUDA... "
CUDA_STATUS=$(python3 << 'EOF'
import torch
if torch.cuda.is_available():
  print(f"CUDA {torch.version.cuda}")
else:
  print("not_available")
EOF
)

if [[ "$CUDA_STATUS" == "not_available" ]]; then
  echo -e "${YELLOW}⚠ CUDA not available. Will use CPU (slow, but OK).${NC}"
else
  echo -e "${GREEN}✓ $CUDA_STATUS${NC}"
fi

# 5. Check cuDNN
echo -n "Checking cuDNN... "
CUDNN_STATUS=$(python3 << 'EOF'
import ctypes
try:
  ctypes.CDLL("libcudnn.so.8")
  print("found")
except OSError:
  print("not_found")
EOF
)

if [[ "$CUDNN_STATUS" == "not_found" ]]; then
  CUDA_CHECK=$(python3 -c "import torch; print('yes' if torch.cuda.is_available() else 'no')")
  if [[ "$CUDA_CHECK" == "yes" ]]; then
    echo -e "${YELLOW}⚠ cuDNN missing but CUDA available. See README troubleshooting.${NC}"
  else
    echo -e "${GREEN}✓ (CPU mode, cuDNN not needed)${NC}"
  fi
else
  echo -e "${GREEN}✓ cuDNN found${NC}"
fi

# 6. Pre-download model
echo
echo "Downloading model large-v3 (~3.2 GB, may take 5-10 min)..."
python3 << 'EOF'
from faster_whisper import WhisperModel
import sys

print("This may take a while. Please wait...", file=sys.stderr)
try:
  model = WhisperModel("large-v3", compute_type="auto")
  print("\n✓ Model downloaded and cached successfully")
except Exception as e:
  print(f"\n✗ Model download failed: {e}", file=sys.stderr)
  sys.exit(1)
EOF

echo
echo "================================================"
echo -e "${GREEN}Setup complete!${NC}"
echo "================================================"
echo
echo "Next steps:"
echo "  1. Activate venv: source .venv/bin/activate"
echo "  2. Start service: ./start.sh"
echo "  3. Check health:  curl http://localhost:8765/health"
echo
