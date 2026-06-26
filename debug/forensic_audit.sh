#!/bin/bash
# ==============================================================================
# Forensic Audit: Manifest Drift & State Init Logic Diagnosis
# ==============================================================================

echo "🔍 --- COMMENCING DISCREPANCY FORENSIC AUDIT ---"

# 1. Root Cause Diagnostic: Inspect the Task Payload
echo -e "\n--- [1/4] Inspecting Validated Task Payload Settings ---"
TASK_FILE=$(find . -name "mesh_generator_task.json" | head -n 1)
if [ -f "$TASK_FILE" ]; then
    echo "✅ Found Task File at: $TASK_FILE"
    echo "📋 Content Filtering for pipeline identifiers:"
    grep -E "pipeline_id|version|manifest" "$TASK_FILE" || cat "$TASK_FILE"
else
    echo "❌ ERROR: Task file 'mesh_generator_task.json' could not be found in workspace."
fi

# 2. File Location Scan: Find what manifests ACTUALLY exist in the cloned repo
echo -e "\n--- [2/4] Scanning Cloned Repository for Available Manifest Files ---"
REPO_DIR="data/testing-input-output/repositories/mesh_generator"
if [ -d "$REPO_DIR" ]; then
    echo "✅ Target repository directory exists."
    echo "📋 Listing all JSON files inside the cloned repository structure:"
    find "$REPO_DIR" -type f -name "*.json" | sed 's/^/  ➡️ /'
else
    echo "❌ ERROR: Cloned repository directory missing at $REPO_DIR"
fi

# 3. Smoking-Gun Source Audit: Inspect breaking lines in initialize_state.py
echo -e "\n--- [3/4] Smoking-Gun Source Code Audit: initialize_state.py ---"
INIT_SCRIPT="src/pipeline/initialize_state.py"
if [ -f "$INIT_SCRIPT" ]; then
    echo "📋 Auditing load_pipeline_manifest block (Lines 75-100):"
    cat -n "$INIT_SCRIPT" | sed -n '75,100p'
    echo -e "\n📋 Auditing main invocation block (Lines 140-165):"
    cat -n "$INIT_SCRIPT" | sed -n '140,165p'
else
    echo "❌ ERROR: Target script $INIT_SCRIPT does not exist at runtime path."
fi

# 4. Automated Repair Hooks (Commented Out for Safety)
echo -e "\n--- [4/4] Automated Repair Hook Blueprints ---"
echo "💡 To auto-heal this drift, uncomment the matching injection hook below in your workflow script:"

# # HOOK A: Force task configuration file to target the new pipeline hash found in the repository
# ACTUAL_MANIFEST_FILE=$(find data/testing-input-output/repositories/mesh_generator -name "mesh_pipeline_*.json" | head -n 1)
# if [ -n "$ACTUAL_MANIFEST_FILE" ]; then
#   NEW_ID=$(basename "$ACTUAL_MANIFEST_FILE" .json)
#   echo "🔧 Injecting repair: Mapping out old hardcoded ID to discovered asset: $NEW_ID"
#   # sed -i "s/mesh_pipeline_c592753/$NEW_ID/g" "data/testing-input-output/repositories/mesh_generator/tasks/mesh_generator_task.json"
#   # sed -i "s/mesh_pipeline_c592753/$NEW_ID/g" "$TASK_FILE"
# fi

# # HOOK B: Fallback modification if the initializer logic needs to accept ANY mesh_pipeline file
# # sed -i "s/search_pattern = f\"{pipeline_id}.json\"/search_pattern = \"mesh_pipeline_*.json\"/g" src/pipeline/initialize_state.py

echo -e "\n--- FORENSIC AUDIT COMPLETE ---"