#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🔍 STARTING FORENSIC AUDIT FOR COLLECTION ERROR IN UNIFIED ORCHESTRATOR"
echo "========================================================================"

# 1. Capture explicit trace log of the collection failure
echo "📋 Step 1: Isolation testing via pytest collection trace..."
pytest tests/test_unified_orchestrator.py --collect-only -vv || true

echo "------------------------------------------------------------------------"

# 2. Run compilation check to find unparsed syntax anomalies 
echo "⚙️ Step 2: Checking Python abstract syntax tree / compilation integrity..."
python3 -m py_compile src/pipeline/unified_orchestrator.py || echo "❌ Compilation failed for source engine!"
python3 -m py_compile tests/test_unified_orchestrator.py || echo "❌ Compilation failed for test suite!"

echo "------------------------------------------------------------------------"

# 3. Simulate bare importing outside pytest runtime boundary conditions
echo "🐍 Step 3: Verifying standard import paths and module dependencies..."
PYTHONPATH="src:src/pipeline" python3 -c "import src.pipeline.unified_orchestrator" 2>&1 || echo "❌ Module import failed!"

echo "------------------------------------------------------------------------"

# 4. Smoking-gun source audits with indexed line references
echo "🔬 Step 4: Line audit of test suite and orchestrator boundaries..."
if [ -f src/pipeline/unified_orchestrator.py ]; then
    echo "📄 src/pipeline/unified_orchestrator.py (First 50 lines):"
    cat -n src/pipeline/unified_orchestrator.py | head -n 50
else
    echo "⚠️ Target source file src/pipeline/unified_orchestrator.py was not detected."
fi

echo ""
echo "📄 tests/test_unified_orchestrator.py (First 30 lines):"
cat -n tests/test_unified_orchestrator.py | head -n 30

echo "------------------------------------------------------------------------"

# 5. Scan for module-level structural risks using grep
echo "🔎 Step 5: Scanning for un-guarded global code or trace statements..."
if [ -f src/pipeline/unified_orchestrator.py ]; then
    echo "Found top-level calls/definitions:"
    grep -nE "^(import |from |print\(|[a-zA-Z0-9_]+ = )" src/pipeline/unified_orchestrator.py || true
fi

echo "------------------------------------------------------------------------"

# 6. Automated Recovery Injections
echo "🛠️ Step 6: Automated Repair Injectors (Commented out template alternatives)"
echo "Uncomment the required sed string to force hot-fixes instantly in runtime:"

# Template A: Safeguard a rogue main() invocation executing on import instead of remaining inside a block guard
# # sed -i 's/^main()$/if __name__ == "__main__":\n    main()/g' src/pipeline/unified_orchestrator.py

# Template B: Force patch broken module imports or path layouts
# # sed -i 's/from uninstalled_package import/import mock as/g' src/pipeline/unified_orchestrator.py

# Template C: Append missing environment injection paths right at line 1 of the test runner
# # sed -i '1s/^/import sys, os; sys.path.insert(0, os.path.abspath("src"))\n/' tests/test_unified_orchestrator.py

echo "========================================================================"
echo "🏁 FORENSIC AUDIT SEQUENCE COMPLETION"
echo "========================================================================"