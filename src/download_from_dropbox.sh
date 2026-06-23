#!/bin/bash
# src/download_from_dropbox.sh
# 📦 Ingestion Orchestrator — Aligned with Deterministic Initialization.

# 1. Environment Guard (Strict Validation)
if [[ -z "${APP_KEY}" || -z "${APP_SECRET}" || -z "${REFRESH_TOKEN}" ]]; then
    echo "❌ ERROR: Missing required credentials (APP_KEY, APP_SECRET, REFRESH_TOKEN)."
    exit 1
fi

# 2. Path Definition (SSoT)
export DROPBOX_FOLDER="/simulators"
export LOCAL_FOLDER="./data/testing-input-output"
export LOG_FILE="./dropbox_download_log.txt"

# 3. Setup
mkdir -p "$LOCAL_FOLDER"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 4. Execution Logic
# The Python script now performs internal DI (Dependency Injection) 
# and handles all authentication logic internally.
echo "🔄 Triggering Python Ingestion Worker..."

python3 -c "
from pathlib import Path
from src.io.dropbox_utils import TokenManager
from src.io.download_from_dropbox import CloudIngestor
import os

# Deterministic Initialization: Config derived from explicit environment input
tm = TokenManager(client_id=os.environ['APP_KEY'], client_secret=os.environ['APP_SECRET'])
ingestor = CloudIngestor(tm, os.environ['REFRESH_TOKEN'], Path(os.environ['LOG_FILE']))

# Execution: Added '.json' to allowed_ext to ensure config files are synced.
# The sync method now supports recursive discovery and folder reconstruction.
ingestor.sync(
    os.environ['DROPBOX_FOLDER'], 
    Path(os.environ['LOCAL_FOLDER']), 
    ['.h5', '.npy', '.json', '.step']
)
"

# 5. Result Verification
if [ $? -eq 0 ]; then
    # Audit check: Count how many files actually landed in the target directory
    FILE_COUNT=$(find "$LOCAL_FOLDER" -type f | wc -l)
    
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "✅ SUCCESS: $FILE_COUNT files synchronized to $LOCAL_FOLDER"
    else
        echo "⚠️  WARNING: Sync reported success but 0 files were downloaded."
        echo "   Check if files in Dropbox match the extensions: .h5, .npy, .json", '.step'
        exit 1
    fi
else
    echo "❌ ERROR: Ingestion failed during Python execution."
    exit 1
fi