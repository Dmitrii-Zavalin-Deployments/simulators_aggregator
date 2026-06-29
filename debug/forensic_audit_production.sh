#!/bin/bash
# src/debug/forensic_audit.sh

# Turn off 'fail fast' to guarantee the script prints full diagnostics even if commands fail
set +e

echo "========================================================================"
echo "🔍 PHASE 1: SYSTEM ENVIRONMENT & RUNTIME DIAGNOSTICS"
echo "========================================================================"
echo "[SYSTEM] Current Time: $(date +'%Y-%m-%d %H:%M:%S')"
echo "[SYSTEM] Python Path:  $(which python3 || which python)"
echo "[SYSTEM] Python Ver:   $(python3 --version || python --version)"

echo -e "\n📦 Active Conda Environments:"
conda info --envs 2>/dev/null || echo "⚠️ Conda binary not in system PATH or uninitialized."

echo -e "\n📦 Active Pip Environment Inventory (Truncated Top 20):"
pip list 2>/dev/null | head -n 25 || echo "⚠️ Pip list unavailable or execution context unhydrated."

echo "========================================================================"
echo "🔬 PHASE 2: SMOKING-GUN SOURCE AUDITS (COMPLIANCE LINE REVIEWS)"
echo "========================================================================"
# Target the entry-point script to analyze top-level imports triggering the error
if [ -f "src/pipeline/initialize_state.py" ]; then
    echo "📄 [Audit] src/pipeline/initialize_state.py (Lines 1-20):"
    cat -n src/pipeline/initialize_state.py | head -n 25
else
    echo "❌ [Error] src/pipeline/initialize_state.py could not be located in workspace root."
fi

# Target the internal I/O utilities module where the missing package is requested
if [ -f "src/io/dropbox_utils.py" ]; then
    echo -e "\n📄 [Audit] src/io/dropbox_utils.py (Lines 1-20):"
    cat -n src/io/dropbox_utils.py | head -n 25
else
    echo "❌ [Error] src/io/dropbox_utils.py could not be located in workspace root."
fi

echo -e "\n📄 [Audit] GHA Workflow File Context Search:"
WORKFLOW_FILE=$(find .github/workflows/ -type f \( -name "*.yml" -o -name "*.yaml" \) | head -n 1)
if [ ! -z "$WORKFLOW_FILE" ]; then
    echo "🎯 Found Active Workflow Manifest: $WORKFLOW_FILE"
    echo "🔍 Scanning for State Machine and Environment Setup invocations:"
    grep -n -A 15 -B 2 "Initialize Pipeline State" "$WORKFLOW_FILE" || grep -n -C 5 "initialize_state.py" "$WORKFLOW_FILE"
else
    echo "❌ [Error] No GHA workflow file discovered inside .github/workflows/"
fi

echo "========================================================================"
echo "🛠️ PHASE 3: AUTOMATED IN-ENVIRONMENT WORKFLOW REPAIRS"
echo "========================================================================"
echo "The following sed routines demonstrate automated fixes to lock environment parity."
echo "Uncomment to run as emergency automated repairs in your workflow sequence."

# Repair Action A: Refactor initialize_state.py to strip out the top-level imports causing the boot-crash
# sed -i 's/^from src.state.tuner_state import TunerState/# from src.state.tuner_state import TunerState/g' src/pipeline/initialize_state.py
# sed -i 's/^from src.io.dropbox_utils import TokenManager/# from src.io.dropbox_utils import TokenManager/g' src/pipeline/initialize_state.py
# sed -i 's/^from src.io.download_from_dropbox import CloudIngestor/# from src.io.download_from_dropbox import CloudIngestor/g' src/pipeline/initialize_state.py

# Repair Action B: Inject a safety installation step inside the active workflow file to bootstrap requests
# sed -i '/- name: .* Initialize Pipeline State/i \      - name: 📦 Bootstrapping Pipeline Layer Dependencies\n        shell: bash -el {0}\n        run: |\n          conda activate tuner-env\n          pip install requests\n' "$WORKFLOW_FILE"

echo "========================================================================"
echo "🎉 Forensic audit phase execution complete."
echo "========================================================================"