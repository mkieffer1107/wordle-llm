#!/bin/bash

# This script:
# 1. Downloads a list of valid Wordle words if not already present.
# 2. Downloads Gemma model weights from Hugging Face to a flat directory.
#
# Usage:
#   ./setup.sh [MODEL_ID] [TARGET_DIR]
#
# If TARGET_DIR is not provided, it will default to models/<model-name>, where <model-name> is the part after the last '/' in MODEL_ID.
#
# Example:
#   ./setup.sh google/gemma-3n-E2B-it
#   (This will download to models/gemma-3n-E2B-it)

set -euo pipefail

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Download model weights
MODEL_ID=${1:-google/gemma-3n-E4B-it}

# Determine TARGET_DIR: use $2 if provided, else derive from MODEL_ID (part after last '/')
if [ -n "${2-}" ]; then
    TARGET_DIR=$2
else
    DERIVED_DIR=${MODEL_ID##*/}
    TARGET_DIR="models/$DERIVED_DIR"
fi

TARGET_DIR=$(eval echo "${TARGET_DIR}")  # expand ~

# Ensure the directory is creatable/writable
mkdir -p "${TARGET_DIR}" || { echo -e "${RED}[✗] Cannot write to ${TARGET_DIR}${NC}" >&2; exit 1; }

# Check CLI supports `download`
if ! huggingface-cli --help | grep -q " download"; then
  echo -e "${RED}[✗] huggingface-cli too old. Upgrade: pip install -U \"huggingface_hub[cli]\"${NC}" >&2
  exit 1
fi

echo -e "${YELLOW}[↓] Downloading ${MODEL_ID} → ${TARGET_DIR}${NC}" >&2

huggingface-cli download "${MODEL_ID}" \
  --local-dir "${TARGET_DIR}" \

# Clean up cache directory
rm -rf "${TARGET_DIR}/.cache"

echo -e "${GREEN}[✓] Setup complete. Word list in: data/valid-words.txt${NC}"
echo -e "${GREEN}[✓] Model files in: ${TARGET_DIR}${NC}"