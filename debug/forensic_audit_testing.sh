#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🔍 FORENSIC AUDIT: NOMINAL FLOW ASSERTION FAILURE (1 != 0)"
echo "========================================================================"

# 1. Diagnostic: Isolate the failing test and capture full traceback
echo "📋 Step 1: Isolating failure in test_pipeline_loop_complete_nominal_flow..."
pytest tests/test_unified_orchestrator.py::TestUnifiedOrchestrator::test_pipeline_loop_complete_nominal_flow -vv

echo "------------------------------------------------------------------------"

# 2. Smoking-gun Audit: Locate all exit points in source
echo "🔬 Step 2: Locating potential exit points in orchestrator..."
grep -n "sys.exit(1)" src/pipeline/unified_orchestrator.py

echo "------------------------------------------------------------------------"

# 3. Smoking-gun Audit: View source lines for context
echo "📄 Step 3: Auditing source lines around exit points..."
sed -n '40,150p' src/pipeline/unified_orchestrator.py | cat -n

echo "------------------------------------------------------------------------"

# 4. Automated Instrumentation/Repair Templates
echo "🛠 Step 4: Repair/Instrumentation Templates"
echo "Uncomment the sed command below to inject debug traces before every exit call."
echo "This will print the exit line number to stdout during test execution."

# # Template: Inject a debug print before every sys.exit(1) to see which one is triggered
# sed -i 's/sys.exit(1)/print(f"DEBUG: About to exit at line {__import__("inspect").currentframe().f_back.f_lineno}"); sys.exit(1)/g' src/pipeline/unified_orchestrator.py

# # Template: Force-override the exit status for testing (Use with caution)
# # sed -i 's/sys.exit(1)/sys.exit(0)/g' src/pipeline/unified_orchestrator.py

echo "========================================================================"
echo "🏁 AUDIT COMPLETE: Review pytest stdout above to see the failure cause."
echo "========================================================================"