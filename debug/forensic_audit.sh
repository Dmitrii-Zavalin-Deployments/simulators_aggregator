#!/bin/bash
# src/debug/forensic_audit.sh
# Deep diagnostic suite to flush hidden buffers and pinpoint provisioning failures.

echo "🔍 --- STARTING ADVANCED FORENSIC AUDIT ---"

# Locate architectural targets
REPO_ROOT=$(find . -name "repositories" -type d | head -n 1)
SETUP_SCRIPT=$(find "$REPO_ROOT" -name "mesh_gen_setup.sh" | head -n 1)
INITIALIZER_SCRIPT="src/pipeline/initialize_state.py"

echo "📍 Target Script Located: $SETUP_SCRIPT"
echo "📍 Initializer Located: $INITIALIZER_SCRIPT"

# 1. DIAGNOSTICS: Check for CRLF/Windows Line Ending Pollution
echo -e "\n💾 --- LINE ENDING AUDIT (Checking for hidden carriage returns) ---"
if grep -q $'\r' "$SETUP_SCRIPT"; then
    echo "❌ CRITICAL SMOKING GUN: Hidden Windows CRLF (\\r) characters detected in shell script!"
else
    echo "✅ Line endings verified as clean Unix LF format."
fi

# 2. SOURCE AUDIT: Inspect the python exception handling and buffering context
echo -e "\n📄 --- INITIALIZER CODE AUDIT (Lines 95-120) ---"
if [ -f "$INITIALIZER_SCRIPT" ]; then
    cat -n "$INITIALIZER_SCRIPT" | sed -n '95,125p'
else
    echo "⚠️ Initializer script not found at expected path."
fi

# 3. LIVE TRIAL RUN: Execute script directly with inherited streams to bypass Python's capture buffer
echo -e "\n⚡ --- LIVE RAW TRIAL RUN (Bypassing Python capture isolation) ---"
echo "Executing setup script directly in the runner to reveal the true stdout/stderr:"
cd "$(dirname "$SETUP_SCRIPT")"
set +e
bash "$(basename "$SETUP_SCRIPT")"
EXEC_CODE=$?
cd - > /dev/null
echo "Exit code from raw execution: $EXEC_CODE"

# 4. REPAIR STATION (Automated Repair Injections)
# Uncomment the target line in your workflow or script to patch on the fly.
echo -e "\n🛠️ --- REPAIR STATION ---"

# REPAIR A: Force Python to use unbuffered output so logs print instantly before crashing
# # sed -i 's/python3 src\/pipeline\/initialize_state.py/python3 -u src\/pipeline\/initialize_state.py/' .github/workflows/*.yml

# REPAIR B: Strip dangerous Windows carriage returns (\r) from the simulator script
# # sed -i 's/\r$//' "$SETUP_SCRIPT"

# REPAIR C: Comment out the pip upgrade command (often breaks pip inside pre-built conda envs)
# # sed -i 's/python -m pip install --upgrade pip/# python -m pip install --upgrade pip/' "$SETUP_SCRIPT"

# REPAIR D: Force pip installations to run unbuffered and ignore cache issues
# # sed -i 's/pip install/pip install --no-cache-dir --log \/tmp\/pip_fail.log/' "$SETUP_SCRIPT"

echo -e "\n✅ --- FORENSIC AUDIT COMPLETE ---"