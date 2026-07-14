#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🔍 FORENSIC AUDIT & AUTO-REPAIR: F-STRING QUOTING SYNTAX"
echo "========================================================================"

# 1. Diagnostic: Grep for the specific quotation syntax collision
echo "📋 Step 1: Identifying line locations of nested double quotes..."
grep -n "__import__(\"" src/pipeline/unified_orchestrator.py || echo "✅ No syntax errors found."

echo "------------------------------------------------------------------------"

# 2. Automated Repair Logic (Heredoc protected)
echo "🛠 Step 2: Repairing nested double quotes with single quotes..."
python3 - <<'EOF'
import sys
file_path = "src/pipeline/unified_orchestrator.py"

try:
    with open(file_path, "r") as f:
        content = f.read()
    
    # Replace the double-quoted inner string with single quotes
    # The heredoc ensures we don't have to escape quotes for the shell
    fixed = content.replace('__import__("inspect")', "__import__('inspect')")
    
    with open(file_path, "w") as f:
        f.write(fixed)
    print("✅ Successfully repaired nested quotes in unified_orchestrator.py")
except Exception as e:
    print(f"❌ Error during repair: {e}")
    sys.exit(1)
EOF

echo "------------------------------------------------------------------------"

# 3. Validation: Check if any errors remain
echo "🔬 Step 3: Verifying fix..."
if grep -q "__import__(\"" src/pipeline/unified_orchestrator.py; then
    echo "❌ ERROR: Syntax errors still detected."
    exit 1
else
    echo "✨ Repair Verified: File is syntactically clean."
fi

echo "========================================================================"
echo "🏁 AUDIT & REPAIR COMPLETE"
echo "========================================================================"