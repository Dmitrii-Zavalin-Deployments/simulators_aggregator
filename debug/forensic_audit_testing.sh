#!/usr/bin/env bash
# ==============================================================================
# src/debug/forensic_audit.sh - Post-Test & Lint Forensic Audit & Repair
# ==============================================================================

set +e
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"; }

log "🔍 --- STARTING LINT FORENSIC AUDIT ---"

log "📜 2. Smoking-gun source audit: Inspecting archive_builder.py violation lines..."
if [ -f "src/io/archive_builder.py" ]; then
    cat -n src/io/archive_builder.py | sed -n '25,40p;95,115p'
else
    log "⚠️ src/io/archive_builder.py not found."
fi

log "📂 3. Repository workspace status..."
git status -s

# ==============================================================================
# 🛠️ AUTOMATED REPAIR INJECTIONS (Commented out with # per policy)
# Root Cause 1 (BLE001): Blind exception catch on config parsing -> use specific exceptions.
# Root Cause 2 (TRY401): Redundant exception variable in logger.exception -> remove `{e}`.
# ==============================================================================

# sed -i 's/except Exception as e:/except (json.JSONDecodeError, KeyError, TypeError, OSError) as e:/g' src/io/archive_builder.py
# sed -i 's/logger.exception(f"CRITICAL: Archive packaging failed: {e}")/logger.exception("CRITICAL: Archive packaging failed")/g' src/io/archive_builder.py

log "✅ --- LINT FORENSIC AUDIT COMPLETE ---"