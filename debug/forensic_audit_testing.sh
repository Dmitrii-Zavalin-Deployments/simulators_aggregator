#!/usr/bin/env bash
# ==============================================================================
# src/debug/forensic_audit.sh - Post-Test & Lint Forensic Audit & Repair
# ==============================================================================

set +e
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }

log "🔍 --- STARTING FORENSIC LINT & CODE AUDIT ---"



log "📜 2. Smoking-gun source audit: Inspecting test file patch context (tests/io/test_upload_to_dropbox.py)..."
if [ -f "tests/io/test_upload_to_dropbox.py" ]; then
    cat -n tests/io/test_upload_to_dropbox.py | grep -E "mock_path_cls|parse_args|CloudUploader" -C 5 || cat -n tests/io/test_upload_to_dropbox.py | head -n 160 | tail -n 30
else
    log "⚠️ test_upload_to_dropbox.py not found in expected path."
fi

log "📂 3. Repository workspace status..."
git status

# ==============================================================================
# 🛠️ AUTOMATED REPAIR INJECTIONS (Commented out with # per policy)
# Root Cause: Ruff F841 local variable `mock_path_cls` assigned but never used.
# Uncomment the # sed lines below to automate the removal of the unused patch argument.
# ==============================================================================

# sed -i '/patch("src.io.upload_to_dropbox.Path") as mock_path_cls:/d' tests/io/test_upload_to_dropbox.py
# sed -i '/patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader,/s/,/ /' tests/io/test_upload_to_dropbox.py

log "✅ --- FORENSIC AUDIT COMPLETE ---"