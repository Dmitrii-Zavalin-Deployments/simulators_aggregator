#!/bin/bash
# ==============================================================================
# Forensic Audit: Syntax Corruption Detection (Merge Conflict Markers)
# ==============================================================================

TARGET="tests/pipeline/test_generate_execution_cmd.py"

echo "🔍 DIAGNOSTICS: Scanning for Git Conflict Artifacts..."

# 1. Audit: Check for conflict markers in the first 20 lines
echo "--- [Audit: First 20 lines of $TARGET] ---"
head -n 20 "$TARGET" | cat -n

echo -e "\n--- [Audit: Searching for markers '<<<<<<<', '=======', '>>>>>>>'] ---"
grep -E "<<<<<<<|=======|>>>>>>>" "$TARGET" || echo "No markers found (the syntax error might be a literal '<<' operator)."

# 2. Automated Repair Proposals
echo -e "\n--- [Automated Repair: Stripping Conflict Markers] ---"
echo "WARNING: This will delete lines containing conflict markers. Review your file manually if possible."

echo "# 1. Remove git conflict marker lines"
# sed -i '/<<<<<<<\|=======\|>>>>>>>/d' "$TARGET"

echo "✅ Forensic audit complete."