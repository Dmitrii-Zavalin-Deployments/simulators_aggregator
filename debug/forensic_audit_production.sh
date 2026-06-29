#!/bin/bash
# ==============================================================================
# 🔍 DEEP FORENSIC AUDIT: SIMULATOR EXECUTION PATH MATCH ENGINE
# ==============================================================================

echo "========================================================================"
echo "🔍 DIAGNOSTICS: Shell Execution Context & Working Directories"
echo "========================================================================"
echo "Current Aggregator Working Directory (CWD): $(pwd)"
echo "Checking Aggregator Root contents: $(ls -F | grep -E 'data/|src/|config/|tasks/')"

# Define absolute paths to targets inside the sub-repository structure
TARGET_REPO_DIR="data/testing-input-output/repositories/mesh_generator"
TARGET_MAIN="$TARGET_REPO_DIR/src/main.py"
TARGET_CONFIG="$TARGET_REPO_DIR/config/config.json"

echo -e "\n--- 📂 PROBING TARGET SUB-REPOSITORY PATHS ---"
if [ -d "$TARGET_REPO_DIR" ]; then
    echo "✅ Found sub-repository workspace directory at: $TARGET_REPO_DIR"
else
    echo "❌ ERROR: Target sub-repository workspace directory does not exist at: $TARGET_REPO_DIR"
fi

if [ -f "$TARGET_CONFIG" ]; then
    echo "✅ Target configuration asset located: $TARGET_CONFIG"
else
    echo "❌ ERROR: Target configuration asset missing at expected path: $TARGET_CONFIG"
fi

echo "========================================================================"
echo "🔎 SMOKING GUN: Source Code Line-by-Line Path Evaluation Audit"
echo "========================================================================"
if [ -f "$TARGET_MAIN" ]; then
    echo "Sub-Repository Main Entry Point: $TARGET_MAIN"
    echo "------------------------------------------------------------------------"
    # Print the lines around file opens to identify un-anchored relative paths
    cat -n "$TARGET_MAIN" | grep -C 7 -E "open\(|config\.json"
else
    echo "❌ CRITICAL ERROR: Unable to locate sub-repository entry point: $TARGET_MAIN"
fi

echo "========================================================================"
echo "🔧 AUTOMATED REPAIRS (Sed Injections)"
echo "========================================================================"
echo "To fix this mismatch in your CI pipeline automatically, uncomment the fields below:"
echo ""
echo "# Strategy A: Enforce contextual directory nesting before execution inside generating blocks"
echo "# sed -i \"s|python3 \${repo_dir}/src/main.py|(cd \${repo_dir} \&\& python3 -m src.main)|g\" src/pipeline/generate_execution_cmd.py"
echo ""
echo "# Strategy B: Direct hotfix inline string adjustment for hardcoded file opens inside sub-repo main"
echo "# sed -i 's|open(\"config/config.json\"|open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), \"config/config.json\"))|g' $TARGET_MAIN"

echo "========================================================================"
echo "🏁 DEEP FORENSIC AUDIT SEQUENCE COMPLETE"
echo "========================================================================"