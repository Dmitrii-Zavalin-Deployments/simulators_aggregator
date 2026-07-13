#!/bin/bash
# -----------------------------------------------------------------------------
# Forensic Audit: Path Resolution & Argument Contract
# Purpose: Diagnose misconfiguration in CI environment paths and arg passing.
# -----------------------------------------------------------------------------

echo "=== [1/5] Environment Diagnostic: Current Working Directory ==="
pwd
ls -F

echo -e "\n=== [2/5] Smoking-Gun Audit: Path Existence ==="
# Check if the base path expected by the engine actually exists
TARGET_PATH="/home/runner/work/simulators_aggregator/simulators_aggregator/data/testing-input-output/repositories/schema_merger_splitter"
if [ -d "$TARGET_PATH" ]; then
    echo "SUCCESS: Target path exists."
    ls -F "$TARGET_PATH"
else
    echo "CRITICAL: Path does not exist: $TARGET_PATH"
    echo "Parent directory contents:"
    ls -F "/home/runner/work/simulators_aggregator/simulators_aggregator/data/testing-input-output/"
fi

echo -e "\n=== [3/5] Code Audit: Argument Parsing in src/main.py ==="
# Audit line 84-86 where the path is constructed
sed -n '80,90p' src/main.py

echo -e "\n=== [4/5] Pipeline Variable Audit ==="
# Verify if the environment variable being passed to the CI job is empty
echo "Checking environment variables for path overrides..."
env | grep "INPUT" || echo "No INPUT environment variables found."

echo -e "\n=== [5/5] Diagnostic Complete ==="
echo "If this was caused by an empty variable in your .yml file, use these repairs:"

# -----------------------------------------------------------------------------
# AUTOMATED REPAIR CANDIDATES (Commented Out):
# 
# 1. If your YAML has: --input_output_folder ${{ inputs.folder }}
#    # sed -i 's/${{ inputs.folder }}/path\/to\/correct\/folder/' .github/workflows/your-workflow.yml
#
# 2. If src/main.py is failing to resolve paths correctly, ensure it defaults safely:
#    # sed -i 's/Path(args.input_output_folder).resolve()/Path(args.input_output_folder or ".").resolve()/' src/main.py
#
# 3. If the path string is being corrupted by concatenation:
#    # sed -i 's|--input_output_folder|data/testing-input-output/|g' your-ci-script.sh
# -----------------------------------------------------------------------------