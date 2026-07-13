#!/bin/bash
# -----------------------------------------------------------------------------
# Forensic Audit: CLI Parameter Contract & Positional Argument Drift
# Purpose: Pinpoint exact line mappings causing argument token ingestion error.
# -----------------------------------------------------------------------------

echo "=== [1/4] Environment Workspace Verification ==="
TARGET_REPO="data/testing-input-output/repositories/schema_merger_splitter"

if [ -d "$TARGET_REPO" ]; then
    echo "✅ Found repository target folder layout at: $TARGET_REPO"
else
    echo "❌ Critical: Target repository folder missing or layout changed."
    exit 1
fi

echo -e "\n=== [2/4] Smoking-Gun Source Audit: Argument Handling in model_4 ==="
# Audit the main entry file using numbered line output to see how parameters are mapped
if [ -f "$TARGET_REPO/src/main.py" ]; then
    echo "Auditing entrypoint parameter contract definitions:"
    cat -n "$TARGET_REPO/src/main.py" | grep -A 25 -B 2 -E "argparse|sys.argv|def main" || cat -n "$TARGET_REPO/src/main.py" | head -n 120
else
    echo "❌ Critical: src/main.py is completely missing from cloned asset."
fi

echo -e "\n=== [3/4] Orchestrator State File Alignment Check ==="
# Verify if the pipeline configuration state matches the expected flags
STATE_FILE="data/testing-input-output/tuning_main/state.json"
if [ -f "$STATE_FILE" ]; then
    echo "Inspecting state tracking metadata definitions for Task 2:"
    grep -A 10 -B 2 "schema_merger_splitter" "$STATE_FILE" || cat "$STATE_FILE"
else
    echo "⚠️ State metadata file not found at: $STATE_FILE"
fi

echo -e "\n=== [4/4] Automated Structural Repairs ==="
echo "Review the output above. If argument parsing matches structural mismatches, use one of these fixes:"

# -----------------------------------------------------------------------------
# AUTOMATED REPAIR INJECTIONS (Commented out for safety):
#
# Option A: If model_4 main.py uses old positional arguments instead of optional flags:
# # sed -i 's/parser.add_argument("input_file_name")/parser.add_argument("--input_file_name", dest="input_file_name")/' data/testing-input-output/repositories/schema_merger_splitter/src/main.py
#
# Option B: If the orchestrator state map is passing the wrong argument style string:
# # sed -i 's/--input_file/--input_file_name/g' data/testing-input-output/tuning_main/state.json
# # sed -i 's/--output_file/--output_file_name/g' data/testing-input-output/tuning_main/state.json
# -----------------------------------------------------------------------------