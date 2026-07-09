#!/bin/bash
# ========================================================================
# FILE: src/debug/forensic_audit.sh
# DESCRIPTION: Automated forensic diagnostics and recovery advisor 
#              for simulator aggregation and module execution failures.
# ========================================================================

set -u # Treat unset variables as an error during diagnostics

echo "🔍 ========================================================================"
echo "🔍               --- SIMULATOR FORENSIC AUDIT ENGINE ---"
echo "🔍 ========================================================================"

# Resolve workspace directory patterns dynamically
BRANCH_NAME="${GITHUB_REF_NAME:-main}"
WORKSPACE_DIR="data/testing-input-output/tuning_${BRANCH_NAME}"
LOG_FILE="${RUNNER_TEMP:-/home/runner/work/_temp}/pipeline_execution.log"
REPO_TARGET="data/testing-input-output/repositories/mesh_generator/src/main.py"

# ========================================================================
# 1. GREP/CAT DIAGNOSTICS FOR CODE/OUTPUT ROOT CAUSES
# ========================================================================
echo -e "\n📊 [STEP 1] Running Grep/Cat Diagnostics on Error Telemetry..."

if [ -f "$LOG_FILE" ]; then
    echo "📋 Found active simulation log layer: $LOG_FILE"
    echo "--- CRITICAL EXCEPTION HIGHLIGHTS ---"
    grep -E -A 3 -B 2 "Traceback|ModuleNotFoundError|Error|Exception" "$LOG_FILE" || echo "No explicit Python crash exceptions found in raw log file."
else
    echo "⚠️ Warning: Raw pipeline log file not found at $LOG_FILE. Scanning failed runs archive..."
    ARCHIVE_DIR="$WORKSPACE_DIR/failed_runs_archive"
    if [ -d "$ARCHIVE_DIR" ]; then
        LATEST_RUN=$(ls -td "$ARCHIVE_DIR"/run_* 2>/dev/null | head -1)
        if [ -n "$LATEST_RUN" ] && [ -f "$LATEST_RUN/telemetry_results.json" ]; then
            echo "📋 Extracting metadata from archived run: $LATEST_RUN"
            cat "$LATEST_RUN/telemetry_results.json" | jq -r '. | {status: .status, exit_code: .exit_code}' 2>/dev/null || cat "$LATEST_RUN/telemetry_results.json"
        fi
    else
        echo "❌ Critical: No execution log or telemetry archive found."
    fi
fi

echo -e "\n🐍 Checking environment package alignment..."
if command -v conda &> /dev/null; then
    echo "Active Conda Environment Packages (jsonschema search):"
    conda list | grep "jsonschema" || echo "❌ jsonschema not found in active conda environment list."
else
    echo "Active Pip Environment Packages (jsonschema search):"
    pip list 2>/dev/null | grep -i "jsonschema" || echo "❌ jsonschema not found in global pip context."
fi

# ========================================================================
# 2. CAT -N FOR SMOKING-GUN SOURCE AUDITS
# ========================================================================
echo -e "\n🎯 [STEP 2] Inspecting Smoking-Gun Code Context..."

if [ -f "$REPO_TARGET" ]; then
    echo "📄 Source File: $REPO_TARGET"
    echo "--- TARGETING CODE BOUNDARY CRASH INDEX (Lines 1-20) ---"
    cat -n "$REPO_TARGET" | head -n 20
else
    echo "❌ Error: Could not locate the target sub-repository main core script at: $REPO_TARGET"
    echo "Current local hierarchy tree layout:"
    find data/testing-input-output/repositories/ -maxdepth 4 -type f 2>/dev/null || echo "No repositories cloned yet."
fi

# ========================================================================
# 3. AUTOMATED REPAIRS VIA SED INJECTIONS (SAFETY DISABLED / MANUAL RECOVERY)
# ========================================================================
echo -e "\n🛠️ [STEP 3] Generating Automated Recovery Vectors..."
echo "To activate automated repairs in the runtime container pipeline loop,"
echo "uncomment the requested repair vector from the forensic block below:"

# INJECTION OPTION A: Inline fallback package provisioner injected before the failing import
# sed -i '7i\try:\n    import jsonschema\nexcept ImportError:\n    import subprocess, sys; subprocess.check_call([sys.executable, "-m", "pip", "install", "jsonschema"])' "$REPO_TARGET"

# INJECTION OPTION B: Wrap the problematic verification call block in a structural try-except loop
# sed -i '/from jsonschema import/c\try:\n    from jsonschema import validate, ValidationError\nexcept ImportError:\n    print("⚠️ FORENSIC WARNING: jsonschema missing. Ingesting stub layer."); validate = lambda *args, **kwargs: True; ValidationError = Exception' "$REPO_TARGET"

# INJECTION OPTION C: Hot-patch a setup requirements layout file before runtime triggers execute
# sed -i '/requirements = \[/a\    "jsonschema",' data/testing-input-output/repositories/mesh_generator/setup.py

echo -e "\n🏁 ========================================================================"
echo "🔍               --- FORENSIC AUDIT MATRIX COMPLETE ---"
echo "========================================================================"