#!/bin/bash
# src/debug/forensic_audit.sh
# Forensic Audit: Diagnosing Python import failures in mesh_generator

REPO_ROOT="data/testing-input-output/repositories/mesh_generator"
MAIN_FILE="$REPO_ROOT/src/main.py"

echo "========================================================================"
echo "🔍 DIAGNOSTICS: Environment and File Structure"
echo "========================================================================"
echo "Current Working Directory: $(pwd)"

echo "Checking existence of repo directory:"
ls -d "$REPO_ROOT" || echo "❌ Repo not found at $REPO_ROOT"

echo "Checking package structure (looking for __init__.py):"
find "$REPO_ROOT" -name "__init__.py"

echo "Checking main.py location:"
ls -l "$MAIN_FILE"

echo "========================================================================"
echo "🔎 SMOKING GUN: Source Audit (Import Path)"
echo "========================================================================"
# Showing lines 1-15 to inspect imports
cat -n "$MAIN_FILE" | head -n 15

echo "========================================================================"
echo "🔧 PROPOSED REMEDIATIONS (Uncomment sed commands to apply)"
echo "========================================================================"
echo "Strategy: If the issue is execution context, we can force-inject the"
echo "repo root into sys.path at the top of main.py."

# 1. Automated Repair: Inject sys.path modification to make 'src' importable
# # sed -i '1i import sys, os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))' "$MAIN_FILE"

# 2. Automated Repair: If the folder name was misspelled (e.g., 'mesh_generator_state.py' vs 'mesh_generator_state')
# # sed -i 's/from src.state.mesh_generator_state/from src.state.mesh_generator_state/g' "$MAIN_FILE"

# 3. Validation check: Print current sys.path to verify if the fix worked
# # sed -i '/import sys/a print(f"DEBUG: sys.path: {sys.path}")' "$MAIN_FILE"

echo "Audit complete. Review the diagnostic output above."