#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🕵️‍♂️ BEGINNING ACE PIPELINE VERIFICATION SUITE"
echo "========================================================================"

REPO_PATH="repositories/fluid_dynamics_simulator"
WORKSPACE_CONFIGS="data/testing-input-output/tuning_main/configs"
STATE_FILE="data/testing-input-output/tuning_main/state.json"

# --- 1. CONFIG ASSET AUDIT ---
echo -e "\n📁 [1/4] AUDITING STAGED CONFIGURATION ASSETS..."
if [ -d "$WORKSPACE_CONFIGS" ]; then
    echo "Files found in workspace configs:"
    ls -l "$WORKSPACE_CONFIGS"
else
    echo "❌ Workspace config directory not found at ${WORKSPACE_CONFIGS}."
fi

# --- 2. SOVEREIGN STATE AUDIT ---
echo -e "\n📜 [2/4] INSPECTING GENERATED SOVEREIGN STATE..."
if [ -f "$STATE_FILE" ]; then
    echo "Contents of ${STATE_FILE}:"
    cat "$STATE_FILE"
else
    echo "❌ State file not found!"
fi

# --- 3. SMOKING-GUN SOURCE AUDIT (initialize_state.py) ---
echo -e "\n🔍 [3/4] AUDITING MATRIX COMPILATION LOGIC (Lines 185-200)..."
FILE="src/pipeline/initialize_state.py"
if [ -f "$FILE" ]; then
    cat -n "$FILE" | sed -n '185,200p'
else
    echo "❌ Missing source file."
fi

# --- 4. PREPARED SED INJECTIONS FOR AUTOMATED REPAIRS ---
echo -e "\n🛠️ [4/4] REMEDIATION SUGGESTIONS..."
# If the state.json is empty or missing keys, you can regenerate it:
# rm data/testing-input-output/tuning_main/state.json && python3 src/pipeline/initialize_state.py

echo "========================================================================"
echo "🏁 VERIFICATION COMPLETED. CHECK 'STATE.JSON' OUTPUT ABOVE. 🏁"
echo "========================================================================"