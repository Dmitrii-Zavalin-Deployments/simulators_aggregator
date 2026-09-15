#!/bin/bash
# ==============================================================================
# src/debug/forensic_audit.sh - Post-Test Failure Forensic Audit & Repair
# ==============================================================================

set +e
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }

log "🔍 --- STARTING POST-TEST FORENSIC AUDIT ---"

log "🔎 1. Searching repository for references to missing test fixture 'navier_stokes_output.zip'..."
grep -rn "navier_stokes_output.zip" . || log "⚠️ String not found via grep, checking broader match..."

log "📜 2. Smoking-gun source audit: Inspecting test file line numbers (tests/io/test_upload_to_dropbox.py)..."
if [ -f "tests/io/test_upload_to_dropbox.py" ]; then
    cat -n tests/io/test_upload_to_dropbox.py
else
    log "⚠️ Standard path not found, locating test_upload_to_dropbox.py..."
    FOUND_TEST=$(find . -name "test_upload_to_dropbox.py" | head -n 1)
    if [ -n "$FOUND_TEST" ]; then
        cat -n "$FOUND_TEST"
    fi
fi

log "📜 3. Inspecting Uploader implementation path handling (src/io/upload_to_dropbox.py)..."
if [ -f "src/io/upload_to_dropbox.py" ]; then
    cat -n src/io/upload_to_dropbox.py | grep -E "upload\(|local_path|exists" -C 3
fi

log "📂 4. Checking existence of temporary or test data directories..."
ls -la data/testing-input-output/ 2>/dev/null || ls -la .

# ==============================================================================
# 🛠️ AUTOMATED REPAIR INJECTIONS (Commented out for safety validation)
# Uncomment the appropriate # sed line below if path binding in test/fixture is misaligned
# ==============================================================================

# sed -i 's/navier_stokes_output\.zip/data\/testing-input-output\/navier_stokes_output.zip/g' tests/io/test_upload_to_dropbox.py
# sed -i '/def test_cloud_uploader_success/a \    (Path("data/testing-input-output") / "navier_stokes_output.zip").touch()' tests/io/test_upload_to_dropbox.py

log "✅ --- POST-TEST FORENSIC AUDIT COMPLETE ---"