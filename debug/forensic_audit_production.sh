#!/usr/bin/env bash
# ==============================================================================
# Target: Forensic Audit & Repair for CFD Compiler Schema Validation Failure
# Description: Diagnoses why aggregated configuration ranges (which wrap values 
#              in lists) are being passed directly to cfd_compiler without 
#              resolution into concrete runtime scalar values.
# ==============================================================================

set -e

echo "========================================================================"
echo "🔍 DIAGNOSTIC PHASE: Grepping for Configuration Loading & CFD Compiler"
echo "========================================================================"

# 1. Search for cfd_compiler invocation or config loading logic
echo "--- Searching for cfd_compiler integration ---"
grep -rn "cfd_compiler" src/ tests/ || true

# 2. Search for boundary_condition_mapping handling
echo -e "\n--- Searching for boundary_condition_mapping references ---"
grep -rn "boundary_condition_mapping" src/ tests/ || true

echo -e "\n========================================================================"
echo "🔎 SMOKING-GUN SOURCE AUDIT (cat -n)"
echo "========================================================================"
# Automatically locate and display the file handling config loading or execution
CONFIG_HANDLER=$(grep -rl "boundary_condition_mapping" src/ 2>/dev/null | head -n 1)
if [ -n "$CONFIG_HANDLER" ]; then
    echo "Inspecting config handler: $CONFIG_HANDLER"
    cat -n "$CONFIG_HANDLER"
else
    echo "⚠️ Warning: No explicit handler found in src/, checking workflow/orchestrator files..."
    grep -rn "tuning_" src/ || true
fi

echo -e "\n========================================================================"
echo "🛠️ AUTOMATED REPAIR INJECTIONS (Commented out)"
echo "========================================================================"
echo "Root Cause Identified: The aggregated configuration contains lists for every "
echo "parameter (e.g., 'location': ['x_min'], 'u': [2.5]), because the aggregation "
echo "script stores unique observed values in arrays. However, cfd_compiler expects "
echo "concrete runtime values (strings and numbers) matching its strict JSON schema."
echo ""
echo "To apply automated remediation (e.g., unwrapping single-item range lists into "
echo "concrete scalar/string values before passing to cfd_compiler), uncomment "
echo "and adapt the appropriate sed/patch injection below:"
echo ""

# # Example sed injection to unpack single-element lists during config loading:
# # sed -i 's/config = json.load(f)/config = unpack_config_ranges(json.load(f))/g' src/core/config_loader.py

echo -e "\n✅ Forensic audit execution completed successfully."