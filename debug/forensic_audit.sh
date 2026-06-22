#!/bin/bash
# Forensic Audit Script: /debug/forensic_audit.sh

echo "--- [DIAGNOSTICS: File Discovery] ---"
# Find where the YAML files are hidden
echo "Searching for any YAML files in the cloned directory..."
find . -name "*.yml" -o -name "*.yaml"

echo -e "\n--- [DIAGNOSTICS: Repo State] ---"
# Navigate to the repo to inspect it
cd mesh_generator || { echo "ERROR: mesh_generator folder not found"; exit 1; }
git branch -a
git status

echo -e "\n--- [SMOKING GUN: Source Audit] ---"
# Check file contents to see if it's a dummy or real file
ls -F | grep ".yml"

# Automated Repairs (Uncomment if needed)
# -------------------------------------------------------------------
# Fix 1: If the file is in a subdirectory (e.g., 'config/mesh_generator.yml')
# sed -i 's|if \[ -f "mesh_generator.yml" \]|if [ -f "config/mesh_generator.yml" ]|g' .github/workflows/phase_1_discovery.yml

# Fix 2: If the file is named 'config.yml' instead of 'mesh_generator.yml'
# sed -i 's/mesh_generator.yml/config.yml/g' .github/workflows/phase_1_discovery.yml
# -------------------------------------------------------------------

echo -e "\nAudit complete."