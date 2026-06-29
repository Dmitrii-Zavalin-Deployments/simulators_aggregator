#!/bin/bash
# src/debug/forensic_audit.sh
# Forensic Audit: Diagnosing missing state.json inside workspace

echo "========================================================================"
echo "🔍 DIAGNOSTICS: Global Workspace File & Path Resolution"
echo "========================================================================"
echo "Current Working Directory: $(pwd)"

echo -e "\n1. Searching for any 'state.json' generated anywhere in the workspace:"
find . -name "state.json" || echo "❌ No state.json found anywhere."

echo -e "\n2. Searching for any JSON files inside data/testing-input-output:"
find data/testing-input-output -name "*.json" 2>/dev/null || echo "❌ No JSON files found in data path."

echo -e "\n3. Inspecting the contents of the zip archive to see if it contains state.json:"
if command -v unzip &> /dev/null && [ -f "data/testing-input-output/tuning_main.zip" ]; then
    unzip -l data/testing-input-output/tuning_main.zip
else
    echo "⚠️ unzip command not available or zip file missing."
fi

echo -e "\n4. Checking for execution errors in pipeline initialization logs:"
if [ -f "download_log.txt" ]; then
    echo "--- Last 20 lines of download_log.txt ---"
    tail -n 20 download_log.txt
fi

echo "========================================================================"
echo "🔎 SMOKING GUN: Source Audits (State Initialization & I/O Pipelines)"
echo "========================================================================"

echo -e "\n--- Auditing src/pipeline/initialize_state.py (Path Construction) ---"
if [ -f "src/pipeline/initialize_state.py" ]; then
    cat -n src/pipeline/initialize_state.py | head -n 50
else
    echo "❌ src/pipeline/initialize_state.py not found."
fi

echo -e "\n--- Auditing src/io/state_manager.py (Write Realization) ---"
if [ -f "src/io/state_manager.py" ]; then
    cat -n src/io/state_manager.py | head -n 40
else
    echo "❌ src/io/state_manager.py not found."
fi

echo "========================================================================"
echo "🔧 AUTOMATED REPAIRS (Uncomment sed injections to apply fixes)"
echo "========================================================================"
echo "Depending on the source audit findings, use one of the repairs below:"

# Strategy A: If initialize_state.py is missing directory creation (os.makedirs) before writing
# # sed -i '/with open/i \    import os; os.makedirs(os.path.dirname(state_path), exist_ok=True)' src/pipeline/initialize_state.py

# Strategy B: If state_manager.py is hardcoding a flat path instead of using the fully resolved target path
# # sed -i 's/open("state.json"/open(path/g' src/io/state_manager.py

# Strategy C: Force synchronization by manually creating a dummy state.json if running a dormant/dry test block
# # sed -i '/FULL SCOPE DIRECTORY LISTING/i mkdir -p data/testing-input-output/tuning_main && echo "{}" > data/testing-input-output/tuning_main/state.json' .github/workflows/*.yml

echo -e "\n========================================================================"
echo "✅ FORENSIC AUDIT COMPLETE"
echo "========================================================================"