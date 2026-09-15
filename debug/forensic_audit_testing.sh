#!/bin/bash
# ==============================================================================
# src/debug/forensic_audit.sh - Post-Test Failure Forensic Audit & Repair
# ==============================================================================

set +e
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }

log "🔍 --- STARTING POST-TEST FORENSIC AUDIT ---"

log "🔎 1. Searching repository for references to 'navier_stokes_output.zip'..."
grep -rn "navier_stokes_output.zip" . || log "⚠️ String not found via grep"

log "📜 2. Smoking-gun source audit: Inspecting test file line numbers (tests/io/test_upload_to_dropbox.py)..."
cat -n tests/io/test_upload_to_dropbox.py | grep -E "navier_stokes_output|stat|exists|upload" -C 3 || cat -n tests/io/test_upload_to_dropbox.py | head -n 60

log "📜 3. Inspecting Uploader implementation path/stat handling (src/io/upload_to_dropbox.py)..."
cat -n src/io/upload_to_dropbox.py | grep -E "stat|exists|upload" -C 5

log "📂 4. Checking current working directory files..."
ls -la

# ==============================================================================
# 🛠️ AUTOMATED REPAIR INJECTIONS (Commented out for safety validation)
# Root Cause: Path.exists() is mocked to True, but local_path.stat().st_size hits the real filesystem for 'navier_stokes_output.zip'.
# Uncomment the appropriate # sed line below to patch stat mocking or create physical fixture/file.
# ==============================================================================

# Option A: Create physical touch file so real .stat() succeeds during unit test mock
# touch navier_stokes_output.zip

# Option B: Patch Path.stat in test_upload_to_dropbox.py to match mock contract
# sed -i '/patch\.object(Path, "exists"/a \        patch\.object(Path, "stat", return_value=type("obj", (), {"st_size": 26}))\\,' tests/io/test_upload_to_dropbox.py

log "✅ --- POST-TEST FORENSIC AUDIT COMPLETE ---"