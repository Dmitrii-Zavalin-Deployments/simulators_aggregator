#!/bin/bash

echo "--- 🕵️ FORENSIC AUDIT: DIAGNOSTIC LOG START ---"
echo "--- Timestamp: $(date) ---"

# 1. DIAGNOSTICS: Check if the file exists and verify permissions
echo -e "\n🔍 [DIAGNOSTIC] Checking for missing memory_profile.log..."
ls -l /tmp/memory_profile.log || echo "⚠️ /tmp/memory_profile.log does not exist."

# 2. DIAGNOSTICS: Look into the pipeline execution log (where the time output might be hiding)
if [ -n "$RUNNER_TEMP" ] && [ -f "$RUNNER_TEMP/pipeline_execution.log" ]; then
    echo -e "\n📂 [DIAGNOSTIC] Inspecting pipeline execution log contents:"
    grep -i "Maximum resident set size" "$RUNNER_TEMP/pipeline_execution.log" || echo "⚠️ String 'Maximum resident set size' not found in execution logs."
else
    echo "⚠️ Pipeline log not found at $RUNNER_TEMP/pipeline_execution.log"
fi

# 3. SMOKING GUN AUDIT: Audit State and Config files
echo -e "\n🔎 [AUDIT] Inspecting Pipeline State JSON..."
cat -n data/testing-input-output/tuning_main/state.json | head -n 20

echo -e "\n🔎 [AUDIT] Inspecting Global Config..."
cat -n config/config.json 2>/dev/null || echo "⚠️ Global config missing."

# 4. AUTOMATED REPAIR INJECTIONS
# The following lines are commented out. To apply, remove the #.
# These injections wrap the grep call in a file existence check to prevent job failure.

# # sed -i '/grep "Maximum resident set size" \/tmp\/memory_profile.log/c\if [ -f /tmp/memory_profile.log ]; then MAX_RSS_KB=$(grep "Maximum resident set size" /tmp/memory_profile.log | awk "{print \$6}"); else MAX_RSS_KB=0; fi' .github/workflows/main.yml

# # sed -i 's|/usr/bin/time -v|/usr/bin/time -v -o /tmp/memory_profile.log|g' .github/workflows/main.yml
# Note: The second sed ensures that time -v explicitly writes to the file path the grep expects.

echo -e "\n--- 🏁 FORENSIC AUDIT COMPLETE ---"