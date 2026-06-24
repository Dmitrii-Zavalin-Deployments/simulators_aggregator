#!/bin/bash
# src/debug/forensic_audit.sh
# Forensic diagnostic suite to identify root causes of provisioning failures.

echo "🔍 --- STARTING FORENSIC AUDIT ---"
REPO_ROOT=$(find . -name "repositories" -type d | head -n 1)
SETUP_SCRIPT=$(find "$REPO_ROOT" -name "mesh_gen_setup.sh" | head -n 1)

echo "📍 Target Script Located: $SETUP_SCRIPT"

# 1. DIAGNOSTICS: Check if packages partially installed
echo -e "\n📦 --- PIP ENVIRONMENT STATE ---"
pip list | grep -E "numpy|h5py|requests|jsonschema" || echo "⚠️ No dependencies found in pip list."

echo -e "\n🐍 --- CONDA ENVIRONMENT STATE ---"
conda list | grep "pythonocc-core" || echo "⚠️ pythonocc-core not found in conda list."

# 2. SOURCE AUDIT: Smoking-gun analysis
echo -e "\n📄 --- SOURCE CODE AUDIT: $SETUP_SCRIPT ---"
cat -n "$SETUP_SCRIPT"

# 3. DIAGNOSTICS: Last 20 lines of pip/conda logs (if they exist in standard paths)
# This assumes the GHA runner might have kept some temp logs
echo -e "\n📋 --- RECENT INSTALLATION ATTEMPTS ---"
# Check if any .log files exist in the repo or temp dirs
find /tmp -name "*.log" -mmin -10 -exec tail -n 20 {} \; 2>/dev/null || echo "No recent log files found."

# 4. REPAIR STATION (Automated Repair Commands)
# Uncomment the desired line to auto-patch the script on the next run.

echo -e "\n🛠️ --- REPAIR STATION ---"
# # sed -i 's/set -e/set -ex/' "$SETUP_SCRIPT"  # ENABLE DEBUG: Trace every command executed
# # sed -i 's/pip install/pip install --no-cache-dir/' "$SETUP_SCRIPT" # CLEAR CACHE: Fixes corrupted downloads
# # sed -i 's/numpy>=2.0.0/numpy/' "$SETUP_SCRIPT" # LOOSEN CONSTRAINTS: Fixes version conflicts
# # sed -i 's/conda install -y -c conda-forge pythonocc-core/conda install -y -c conda-forge pythonocc-core=7.8.1/' "$SETUP_SCRIPT" # PIN VERSION: Fixes resolution issues

echo -e "\n✅ --- AUDIT COMPLETE ---"