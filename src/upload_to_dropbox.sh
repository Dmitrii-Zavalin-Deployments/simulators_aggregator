#!/bin/bash
# src/upload_to_dropbox.sh
# 📤 Dropbox Upload Orchestrator — Professional Cloud Export Gate.

# 1. Environment Guard
if [[ -z "${APP_KEY}" || -z "${APP_SECRET}" || -z "${REFRESH_TOKEN}" ]]; then
    echo "❌ ERROR: Missing required credentials."
    exit 1
fi

# 2. Path Resolution
# We look for the zip in the testing-input-output folder where the solver usually outputs
BASE_WORK_DIR=$(pwd)
OUTPUT_TO_UPLOAD="${BASE_WORK_DIR}/data/testing-input-output/mesh_generator_output.json"
export LOCAL_ZIP_PATH="${1:-$OUTPUT_TO_UPLOAD}"

# 3. Validation
if [ ! -f "$LOCAL_ZIP_PATH" ]; then
    echo "❌ ERROR: Target file not found at $LOCAL_ZIP_PATH."
    # List directory to help debug why it's missing in logs
    ls -R data/
    exit 1
fi

export PYTHONPATH="${PYTHONPATH}:${BASE_WORK_DIR}"

echo "🔄 Triggering Python CloudUploader for: $LOCAL_ZIP_PATH"

# 4. Execution
python3 -c "
from pathlib import Path
from src.io.dropbox_utils import TokenManager
from src.io.upload_to_dropbox import CloudUploader
import os

# Deterministic Init
tm = TokenManager(client_id=os.environ['APP_KEY'], client_secret=os.environ['APP_SECRET'])
uploader = CloudUploader(tm, os.environ['REFRESH_TOKEN'])

# Execute
uploader.upload(
    Path(os.environ['LOCAL_ZIP_PATH']), 
    '/simulators'
)
"

# 5. Final Result Audit
if [ $? -eq 0 ]; then
    echo "✅ PIPELINE COMPLETE: Upload successful."
else
    echo "❌ CRITICAL ERROR: Dropbox upload failed."
    exit 1
fi