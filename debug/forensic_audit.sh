#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🕵️‍♂️ BEGINNING ACE PIPELINE FORENSIC AUDIT (MISSING ASSET WARNING)"
echo "========================================================================"

REPO_PATH="repositories/fluid_dynamics_simulator"
MISSING_ASSET="mesh_config_01"

# --- 1. GREP DIAGNOSTICS FOR CODES & MANIFEST INTENT ---
echo -e "\n🔍 [1/4] SCANNING MANIFESTS FOR ASSET DECLARATIONS..."
if [ -d "$REPO_PATH" ]; then
    echo "Grepping for references to '${MISSING_ASSET}' inside the library:"
    grep -rn "$MISSING_ASSET" "$REPO_PATH" || echo "❌ No asset reference found in text files."
else
    echo "❌ Repository path not found."
fi

# --- 2. FILESYSTEM DIAGNOSTICS FOR CONFIGURATION ASSETS ---
echo -e "\n📁 [2/4] LOCATING ALL AVAILABLE CONFIGURATION ASSETS..."
echo "Searching for any JSON/YAML configuration files in the library repo structure:"
find "$REPO_PATH" -type f \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) | sort

# --- 3. SMOKING-GUN SOURCE AUDIT (cat -n) ---
echo -e "\n📜 [3/4] PRINTING ASSET VALIDATION CALL STACK (initialize_state.py)..."
FILE="src/pipeline/initialize_state.py"
if [ -f "$FILE" ]; then
    # Audit the configuration processing and validation loop (typically lines 160-195)
    echo "Lines 160 to 195 from ${FILE}:"
    cat -n "$FILE" | sed -n '160,195p'
else
    echo "❌ Missing source file: $FILE"
fi

# --- 4. PREPARED SED INJECTIONS FOR AUTOMATED REPAIRS ---
echo -e "\n🛠️ [4/4] REMEDIATION SUGGESTIONS (UNCOMMENT TO APPLY)..."

# Repair Option A: If the manifest points to 'mesh_config_01' but the file is actually named 'mesh_config.json'
# sed -i 's/"mesh_config_01"/"mesh_config"/g' repositories/fluid_dynamics_simulator/pipelines/mesh_pipeline.json

# Repair Option B: Bypass asset validation check in python if assets are downloaded dynamically later
# sed -i 's/logger.warning(f"⚠️ Asset '\''{config_id}'\'' not found in repo.")/logger.info(f"Asset checked: {config_id}")/g' src/pipeline/initialize_state.py

echo "========================================================================"
echo "🏁 FORENSIC AUDIT SEQUENCE COMPLETED 🏁"
echo "========================================================================"