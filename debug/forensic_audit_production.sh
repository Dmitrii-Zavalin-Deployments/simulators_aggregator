#!/bin/bash
# ==============================================================================
# 🔍 DEEP FORENSIC AUDIT: CAD STEP FILE GEOMETRY INGESTION MISMATCH
# ==============================================================================

echo "========================================================================"
echo "📂 DIAGNOSTICS: Target Asset Presence & File Properties"
echo "========================================================================"
TARGET_STEP="data/testing-input-output/tuning_main/inputs-outputs/sample_geometry.step"
INGESTION_CODE="data/testing-input-output/repositories/mesh_generator/src/steps/ingestion.py"

if [ -f "$TARGET_STEP" ]; then
    echo "✅ Target asset located at: $TARGET_STEP"
    echo "File Size: $(wc -c < "$TARGET_STEP") bytes"
else
    echo "❌ CRITICAL ERROR: Target STEP file asset missing at: $TARGET_STEP"
fi

echo "========================================================================"
echo "🔎 SMOKING GUN: Step File Header & Syntax Line Audit"
echo "========================================================================"
if [ -f "$TARGET_STEP" ]; then
    echo "Top 10 lines of $TARGET_STEP:"
    echo "------------------------------------------------------------------------"
    cat -n "$TARGET_STEP" | head -n 10
else
    echo "❌ Cannot perform syntax audit; file does not exist."
fi

echo -e "\n--- Checking Ingestion Error Anchor Logic ---"
if [ -f "$INGESTION_CODE" ]; then
    cat -n "$INGESTION_CODE" | grep -C 5 "RuntimeError"
else
    echo "⚠️ Ingestion step source file not accessible at this path context."
fi

echo "========================================================================"
echo "🔧 AUTOMATED REPAIRS (Sed & Echo Asset Injections)"
echo "========================================================================"
echo "If your sample_geometry.step is a placeholder string that is breaking the CAD"
echo "kernel parser, uncomment the command below to inject a valid, minimal STEP file structure:"
echo ""
echo "# Strategy: Overwrite the mock file with a syntactically correct, empty ISO-10303-21 schema envelope"
echo "# echo -e \"ISO-10303-21;\\nHEADER;\\nFILE_DESCRIPTION(('STRICT_MOCK'),'2;1');\\nFILE_NAME('sample.step','2026-06-29',('Dmitrii'),('Zavalin Engineering'),'','','');\\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN_CC2'));\\nENDSEC;\\nDATA;\\nENDSEC;\\nEND-ISO-10303-21;\" > $TARGET_STEP"

echo "========================================================================"
echo "🏁 DEEP FORENSIC AUDIT SEQUENCE COMPLETE"
echo "========================================================================"