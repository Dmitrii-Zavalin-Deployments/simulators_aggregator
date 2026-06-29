#!/bin/bash
# src/debug/forensic_audit.sh
# Forensic Audit: Diagnosing Python ModuleNotFoundError in nested sub-repository execution

SUB_REPO_ROOT="data/testing-input-output/repositories/mesh_generator"
SUB_REPO_MAIN="$SUB_REPO_ROOT/src/main.py"

echo "========================================================================"
echo "🔍 DIAGNOSTICS: Python Environment & Path Resolutions"
echo "========================================================================"
echo "Current Working Directory: $(pwd)"
echo "Current PYTHONPATH Envar: ${PYTHONPATH:-[NOT SET]}"

echo -e "\n1. Simulating Python path evaluation for the sub-repository root:"
python3 -c "
import sys, os
sub_repo = os.path.abspath('$SUB_REPO_ROOT')
sub_repo_src = os.path.abspath('$SUB_REPO_ROOT/src')
print(f'Sub-repo absolute root: {sub_repo}')
print(f'Sub-repo absolute src:  {sub_repo_src}')
print(f'Is sub-repo root in sys.path? {sub_repo in sys.path}')
"

echo -e "\n2. Verifying structural existence of the target module file:"
if [ -f "$SUB_REPO_ROOT/src/state/mesh_generator_state.py" ]; then
    echo "✅ Found: $SUB_REPO_ROOT/src/state/mesh_generator_state.py"
else
    echo "❌ Missing: $SUB_REPO_ROOT/src/state/mesh_generator_state.py"
fi

echo -e "\n3. Searching for orchestration scripts that invoke this sub-engine:"
find src/pipeline -type f -name "*.py" | while read -r script; do
    if grep -q "mesh_generator" "$script"; then
        echo "📍 Found reference in: $script"
        grep -n "mesh_generator" "$script"
    fi
done

echo "========================================================================"
echo "🔎 SMOKING GUN: Source Audits (Import Structure & Exec Blocks)"
echo "========================================================================"

echo -e "\n--- Line-by-Line Inspection: Sub-Repository Entry Point ($SUB_REPO_MAIN) ---"
if [ -f "$SUB_REPO_MAIN" ]; then
    cat -n "$SUB_REPO_MAIN" | head -n 25
else
    echo "❌ $SUB_REPO_MAIN not found."
fi

echo "========================================================================"
echo "🔧 AUTOMATED REPAIRS (Uncomment sed injections to apply fixes)"
echo "========================================================================"
echo "Select the appropriate resolution strategy below based on your architecture:"

# Strategy A: Standardize the sub-repository's internal imports to be relative to its own 'src/' directory
# # sed -i 's/from src.state.mesh_generator_state/from state.mesh_generator_state/g' data/testing-input-output/repositories/mesh_generator/src/main.py

# Strategy B: Dynamic path insertion at the very top of the sub-repo main.py before imports break
# # sed -i '1s/^/import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))); /' data/testing-input-output/repositories/mesh_generator/src/main.py

# Strategy C: Inject PYTHONPATH environment variables directly into the parent orchestration execution runner step inside the workflow
# # sed -i '/run:.*matrix_exploder.py/i \          export PYTHONPATH=$PYTHONPATH:$(pwd)/data/testing-input-output/repositories/mesh_generator' .github/workflows/*.yml

echo -e "\n========================================================================"
echo "✅ FORENSIC AUDIT COMPLETE"
echo "========================================================================"