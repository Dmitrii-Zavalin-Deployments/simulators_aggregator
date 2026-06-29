#!/bin/bash
# ==============================================================================
# FORENSIC AUDIT: Path Resolution Diagnostics
# ==============================================================================

echo "--- 🔍 CWD and FILE PROBE ---"
echo "Current Working Directory: $(pwd)"
echo "Checking for config/config.json in CWD: $(ls config/config.json 2>/dev/null || echo 'NOT FOUND')"
echo "Checking for mesh_generator/config/config.json: $(ls data/testing-input-output/repositories/mesh_generator/config/config.json 2>/dev/null || echo 'NOT FOUND')"

echo -e "\n--- 🔎 SMOKING GUN: src/main.py (Failing Lines) ---"
cat -n src/main.py | grep -C 5 "open("

echo -e "\n--- 🛠️ AUTOMATED REPAIRS (Copy-Paste these to fix) ---"
echo "Strategy: Define REPO_ROOT and prepend to all file opens."

# 1. Define REPO_ROOT at the top of src/main.py (Line 8)
# sed -i '8i REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))' src/main.py

# 2. Fix the config loading line (requires manual check of line number)
# sed -i 's|open("config/config.json"|open(os.path.join(REPO_ROOT, "config/config.json")|g' src/main.py

# 3. Fix the schema loading line
# sed -i 's|open(schema_path|open(os.path.join(REPO_ROOT, schema_path)|g' src/main.py

echo -e "\n--- 🏁 FORENSIC AUDIT COMPLETE ---"