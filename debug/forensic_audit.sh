#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🕵️‍♂️ BEGINNING ACE PIPELINE FORENSIC AUDIT (PROVISIONING FAILURE)"
echo "========================================================================"

# --- 1. FILE EXISTENCE & PATH SEARCH ---
echo -e "\n📁 [1/4] LOCATING MISSING SETUP SCRIPT..."
REPO_PATH="repositories/fluid_dynamics_simulator"
# The script reported missing by the error:
TARGET_SCRIPT_NAME="mesh_gen_setup.sh"

echo "Searching for '${TARGET_SCRIPT_NAME}' recursively starting from ${REPO_PATH}..."
find "${REPO_PATH}" -name "${TARGET_SCRIPT_NAME}" || echo "❌ Script not found anywhere in repo."

# --- 2. DIAGNOSTIC SOURCE AUDIT ---
echo -e "\n🔍 [2/4] AUDITING EXECUTION LOGIC..."
FILE="src/pipeline/initialize_state.py"
echo "Printing 'execute_setup_script' logic (lines 86-110):"
cat -n "$FILE" | sed -n '86,110p'

# --- 3. PATH CONSTRUCTION VERIFICATION ---
echo -e "\n🛠️ [3/4] SIMULATING PATH RESOLUTION..."
# This mirrors your Python logic
script_path_in_manifest="setup_scripts/mesh_gen_setup.sh"
echo "Constructed Path: ${REPO_PATH}/${script_path_in_manifest}"
[ -f "${REPO_PATH}/${script_path_in_manifest}" ] && echo "✅ Path resolves to file." || echo "❌ Path is broken."

# --- 4. PREPARED SED INJECTIONS FOR AUTOMATED REPAIRS ---
echo -e "\n🩹 [4/4] REMEDIATION SUGGESTIONS (UNCOMMENT TO APPLY)..."

# 1. Inject diagnostic print to see EXACT path Python thinks it is building
# sed -i '/logger.info(f"⚙️ Executing provisioning script:/i \        logger.info(f"DEBUG: Attempting to run {full_script_path}")' src/pipeline/initialize_state.py

# 2. If the file is actually in the root, remove the 'setup_scripts/' prefix logic
# sed -i 's|full_script_path = repo_path / script_path|full_script_path = repo_path / script_path.split("/")[-1]|g' src/pipeline/initialize_state.py

# 3. If the directory is named incorrectly (e.g., 'scripts/' instead of 'setup_scripts/'), fix the string here:
# sed -i 's|setup_scripts/|scripts/|g' src/pipeline/initialize_state.py

echo "========================================================================"
echo "🏁 AUDIT COMPLETED. CHECK FIND RESULTS ABOVE. 🏁"
echo "========================================================================"