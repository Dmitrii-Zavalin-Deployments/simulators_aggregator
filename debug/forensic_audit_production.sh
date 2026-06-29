#!/bin/bash
# ==============================================================================
# 🔍 FORENSIC AUDIT: WORKSPACE HYDRATION FAILURE
# ==============================================================================

TARGET_DIR="data/testing-input-output/tuning_main"
TARGET_INPUTS="$TARGET_DIR/inputs-outputs"

echo "========================================================================"
echo "🔎 DIAGNOSTICS: Workspace & Environment Context"
echo "========================================================================"
echo "Current Working Directory: $(pwd)"
echo "Listing root directory structure:"
ls -F

echo -e "\n🔎 Searching for missing assets globally:"
find . -name "state.json"
find . -name "cube_50-50-50.step"

echo -e "\n========================================================================"
echo "🔎 SMOKING-GUN AUDIT: Scaffolding Logic"
echo "========================================================================"
# Check if the setup script exists and is executable
if [ -d "repositories/fluid_dynamics_simulator/setup_scripts" ]; then
    echo "Found setup scripts directory. Checking permissions:"
    ls -l repositories/fluid_dynamics_simulator/setup_scripts/
else
    echo "⚠️ Setup scripts directory not found in repository."
fi

echo -e "\n========================================================================"
echo "🔧 AUTOMATED REPAIRS: Emergency Seeding & Path Correction"
echo "========================================================================"
# If assets are found elsewhere in the repo, seed them into the target directory
# to allow the pipeline to proceed (Emergency Fallback)

# Attempt to locate and seed state.json
STATE_FILE=$(find . -name "state.json" | head -n 1)
if [ ! -z "$STATE_FILE" ] && [ ! -f "$TARGET_DIR/state.json" ]; then
    echo "Found state.json at $STATE_FILE. Copying to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    cp "$STATE_FILE" "$TARGET_DIR/state.json"
fi

# Attempt to locate and seed the step file
STEP_FILE=$(find . -name "cube_50-50-50.step" | head -n 1)
if [ ! -z "$STEP_FILE" ] && [ ! -f "$TARGET_INPUTS/cube_50-50-50.step" ]; then
    echo "Found step file at $STEP_FILE. Copying to $TARGET_INPUTS..."
    mkdir -p "$TARGET_INPUTS"
    cp "$STEP_FILE" "$TARGET_INPUTS/cube_50-50-50.step"
fi

# # sed -i 's|relative/path/to/data|data/testing-input-output/tuning_main|g' src/pipeline/initialize_state.py
# # sed -i 's|os.getcwd()|"/home/runner/work/simulators_aggregator/simulators_aggregator"|g' src/io/state_manager.py

echo "========================================================================"
echo "🏁 FORENSIC AUDIT SEQUENCE COMPLETE"
echo "========================================================================"