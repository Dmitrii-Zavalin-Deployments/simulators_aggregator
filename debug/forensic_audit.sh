#!/bin/bash
# ==============================================================================
# Forensic Audit: Path Misconfiguration Diagnosis
# ==============================================================================

echo "🔍 --- COMMENCING FORENSIC AUDIT ---"
echo "Current Directory: $(pwd)"
echo "Target Workspace Env: $WORKSPACE_DIR"

# 1. Smoking-Gun: Audit Python Generator Logic
echo -e "\n--- [1/3] Auditing Python Generator Code ---"
cat -n src/pipeline/generate_provision_cmd.py | grep -A 5 "source_config_asset ="

# 2. Path Discovery: Locate the missing file regardless of directory depth
echo -e "\n--- [2/3] Locating Missing Asset (Recursive Find) ---"
TARGET_FILENAME="mesh_config_0970b4d.json"
echo "Searching for $TARGET_FILENAME in project root..."
find . -name "$TARGET_FILENAME"

# 3. Environment Tree Check
echo -e "\n--- [3/3] Listing relevant data directory structure ---"
if [ -d "data" ]; then
    ls -R data | grep -E "tuning|configs" | head -n 20
else
    echo "❌ ERROR: 'data/' directory is missing or empty."
fi

# ==============================================================================
# AUTOMATED REPAIR HOOKS (Commented out for safety)
# Uncomment the specific line to execute the fix in the CI runner.
# ==============================================================================

# Repair 1: If file is in 'data/configs/' but script looks in 'data/tuning_main/configs/'
# # sed -i 's|os.path.join(base_dir, "configs", config_filename)|os.path.join("data", "configs", config_filename)|g' src/pipeline/generate_provision_cmd.py

# Repair 2: If the folder name is actually lowercase/uppercase mismatch
# # sed -i 's|tuning_main|tuning_MAIN|g' src/pipeline/generate_provision_cmd.py

# Repair 3: If 'configs/' folder doesn't exist and files are in root
# # sed -i 's|os.path.join(base_dir, "configs", config_filename)|os.path.join(base_dir, config_filename)|g' src/pipeline/generate_provision_cmd.py

echo -e "\n--- FORENSIC AUDIT COMPLETE ---"