#!/bin/bash
# src/download_from_dropbox.sh
# 📦 Ingestion Orchestrator — Parametric Version

# 1. Environment Guard
if [[ -z "${APP_KEY}" || -z "${APP_SECRET}" || -z "${REFRESH_TOKEN}" ]]; then
    echo "❌ ERROR: Missing required credentials."
    exit 1
fi

# 2. Argument Handling (Optional: Specific ZIP name)
TARGET_FILE=$1
export DROPBOX_FOLDER="/simulators"
export LOCAL_FOLDER="./data/testing-input-output"

mkdir -p "$LOCAL_FOLDER"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🔄 Triggering Python Ingestion Worker..."

python3 -c "
import sys
from pathlib import Path
from src.io.dropbox_utils import TokenManager
from src.io.download_from_dropbox import CloudIngestor
import os

tm = TokenManager(client_id=os.environ['APP_KEY'], client_secret=os.environ['APP_SECRET'])
ingestor = CloudIngestor(tm, os.environ['REFRESH_TOKEN'], Path('./dropbox_download_log.txt'))

target_file = sys.argv[1] if len(sys.argv) > 1 else None

if target_file:
    print(f'📥 Downloading specific archive: {target_file}')
    # Download logic assumes a method exists, or we treat the path as a remote file
    ingestor.download_file(os.environ['DROPBOX_FOLDER'] + '/' + target_file, Path(os.environ['LOCAL_FOLDER']) / target_file)
else:
    print('🔄 Performing full directory sync...')
    ingestor.sync(os.environ['DROPBOX_FOLDER'], Path(os.environ['LOCAL_FOLDER']), ['.h5', '.npy', '.json', '.step', '.zip'])
" "$TARGET_FILE"

# 3. Result Verification
if [ $? -eq 0 ]; then
    echo "✅ SUCCESS: Ingestion operation complete."
else
    echo "❌ ERROR: Ingestion failed."
    exit 1
fi