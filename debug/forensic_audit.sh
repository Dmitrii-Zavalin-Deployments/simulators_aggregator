#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🕵️‍♂️ BEGINNING ACE PIPELINE VERIFICATION SUITE"
echo "========================================================================"

REPO_PATH="repositories/fluid_dynamics_simulator"
WORKSPACE_CONFIGS="data/testing-input-output/tuning_main/configs"
STATE_FILE="data/testing-input-output/tuning_main/state.json"

# --- 1. CONFIG ASSET AUDIT ---
echo -e "\n📁 [1/5] AUDITING STAGED CONFIGURATION ASSETS..."
if [ -d "$WORKSPACE_CONFIGS" ]; then
    echo "Files found in workspace configs:"
    ls -l "$WORKSPACE_CONFIGS"
else
    echo "❌ Workspace config directory not found at ${WORKSPACE_CONFIGS}."
fi

# --- 2. RUNTIME ENVIRONMENT AUDIT ---
echo -e "\n🧪 [2/5] AUDITING PYTHON DEPENDENCIES..."
# Checking standard libs
DEPENDENCIES=("numpy" "h5py" "requests" "jsonschema")
for pkg in "${DEPENDENCIES[@]}"; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "✅ $pkg is importable."
    else
        echo "❌ $pkg is NOT found."
    fi
done

# Checking OCC (pythonocc-core) specifically
if python3 -c "from OCC.Core.BRep import BRep_Builder; print('OCC Import Success')" > /dev/null 2>&1; then
    echo "✅ pythonocc-core (OCC) is importable."
else
    echo "❌ OCC is NOT found or failed to import."
fi

# --- 3. SOVEREIGN STATE AUDIT ---
echo -e "\n📜 [3/5] INSPECTING GENERATED SOVEREIGN STATE..."
if [ -f "$STATE_FILE" ]; then
    echo "Contents of ${STATE_FILE}:"
    cat "$STATE_FILE"
else
    echo "❌ State file not found!"
fi

# --- 4. SMOKING-GUN SOURCE AUDIT ---
echo -e "\n🔍 [4/5] AUDITING MATRIX COMPILATION LOGIC..."
FILE="src/pipeline/initialize_state.py"
cat -n "$FILE" | sed -n '185,200p'

# --- 5. VERIFICATION COMPLETE ---
echo -e "\n========================================================================"
echo "🏁 VERIFICATION COMPLETED. 🏁"
echo "========================================================================"