#!/bin/bash
# ==============================================================================
# 🔍 DEEP FORENSIC AUDIT: ENVIRONMENT MAPPING & FILE VALIDATION
# ==============================================================================

TARGET_DIR="data/testing-input-output/tuning_main/inputs-outputs"
TARGET_FILE="$TARGET_DIR/cube_50-50-50.step"

echo "========================================================================"
echo "🌍 ENVIRONMENT TRUTH: Where is the CI runner actually looking?"
echo "========================================================================"
echo "Working Directory: $(pwd)"
echo "Full path expected: $(realpath "$TARGET_FILE" 2>/dev/null || echo 'Path invalid')"

echo -e "\n🔎 Searching for all .step files in this workspace (Looking for duplicates/shadows):"
find . -name "*.step" -ls

echo -e "\n========================================================================"
echo "📂 ASSET INTEGRITY: The 'Real' File Stats"
echo "========================================================================"
if [ -f "$TARGET_FILE" ]; then
    ls -lh "$TARGET_FILE"
    echo -n "File Type (encoding): "
    file "$TARGET_FILE"
else
    echo "❌ CRITICAL: The file $TARGET_FILE does not exist in this specific environment."
    exit 1
fi

echo -e "\n========================================================================"
echo "🔎 SMOKING GUN: Raw Binary Header Audit"
echo "========================================================================"
# This prints the first 50 bytes in a visual format to catch hidden characters/BOMs
echo "First 50 bytes (Hex/ASCII visual):"
head -c 50 "$TARGET_FILE" | od -c

echo -e "\n\nChecking for the mandatory ISO header string at line 1:"
head -n 1 "$TARGET_FILE" | grep -q "ISO-10303-21" && echo "✅ Header match found!" || echo "❌ MISSING: Does not start with ISO-10303-21"

echo -e "\n========================================================================"
echo "🔧 AUTOMATED REPAIRS (Potential Remediation)"
echo "========================================================================"
echo "If this was a Windows line-ending issue, uncomment to fix:"
# # sed -i 's/\r$//' "$TARGET_FILE"

echo "If the file is completely wrong/empty and you need to force-overwrite (DANGEROUS):"
# # echo -e "ISO-10303-21;..." > "$TARGET_FILE"

echo "========================================================================"
echo "🏁 DEEP FORENSIC AUDIT SEQUENCE COMPLETE"
echo "========================================================================"