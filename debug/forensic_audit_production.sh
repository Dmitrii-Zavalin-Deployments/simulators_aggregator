#!/bin/bash
# ==============================================================================
# 🔍 FORENSIC AUDIT: INPUT ASSET HYDRATION FAILURE
# ==============================================================================

TARGET_ASSET="cube_50-50-50.step"
TARGET_DIR="data/testing-input-output/tuning_main/inputs-outputs"
INITIALIZATION_LOGIC="src/pipeline/initialize_state.py"

echo "========================================================================"
echo "🔎 DIAGNOSTICS: Asset Hunt & Path Verification"
echo "========================================================================"

# 1. Search for the file in the entire repository to check for misplacement
echo "Searching for '$TARGET_ASSET' anywhere in workspace..."
find . -name "$TARGET_ASSET" -not -path '*/.*'

# 2. Check the contents of the expected directory
echo -e "\nListing contents of expected target directory: $TARGET_DIR"
ls -lah "$TARGET_DIR" 2>/dev/null || echo "Target directory does not exist yet."

echo -e "\n========================================================================"
echo "🔎 SMOKING-GUN SOURCE AUDIT: Path Validation Logic"
echo "========================================================================"
# 3. Locate the error message in the codebase to see how it checks existence
echo "Inspecting '$INITIALIZATION_LOGIC' for file validation logic:"
grep -n "Required input asset" "$INITIALIZATION_LOGIC"
echo -e "\nSnippet of validation block:"
cat -n "$INITIALIZATION_LOGIC" | grep -A 10 "Required input asset"

echo -e "\n========================================================================"
echo "🔧 AUTOMATED REPAIRS VIA SED INJECTIONS"
echo "========================================================================"
echo "If the file is misaligned, use these to fix paths or force creation:"

# # Repair: If the path is hardcoded incorrectly in the orchestrator, fix the base path:
# # sed -i 's|old_path/inputs-outputs|data/testing-input-output/tuning_main/inputs-outputs|g' "$INITIALIZATION_LOGIC"

# # Repair: If the asset is buried in a subfolder (e.g., 'dummies'), pull it to the target:
# # cp tests/dummies/sample_geometry.step "$TARGET_DIR/$TARGET_ASSET"

# # Repair: Create a placeholder file if the pipeline requires existence but not specific data:
# # touch "$TARGET_DIR/$TARGET_ASSET"

echo "========================================================================"
echo "🏁 FORENSIC AUDIT SEQUENCE COMPLETE"
echo "========================================================================"