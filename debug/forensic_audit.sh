#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo "🕵️‍♂️ BEGINNING ACE PIPELINE FORENSIC AUDIT (CODE 127 DIAGNOSTICS)"
echo "========================================================================"

TARGET="repositories/fluid_dynamics_simulator/setup_scripts/mesh_gen_setup.sh"

# --- 1. FILE INTEGRITY & HIDDEN CHAR DIAGNOSIS ---
echo -e "\n📁 [1/4] AUDITING FILE ENDINGS (LOOK FOR 'CRLF')..."
if [ -f "$TARGET" ]; then
    echo "Checking file format:"
    file "$TARGET"
    
    echo -e "\nChecking for hidden Carriage Return (^M) characters (cat -A):"
    cat -A "$TARGET" | head -n 2
else
    echo "❌ File not found at expected path."
fi

# --- 2. SMOKING-GUN SOURCE AUDIT (cat -n) ---
echo -e "\n🔍 [2/4] AUDITING EXECUTION SOURCE (initialize_state.py)..."
FILE="src/pipeline/initialize_state.py"
echo "Printing lines 105-115 of ${FILE}:"
cat -n "$FILE" | sed -n '105,115p'

# --- 3. PERMISSIONS AUDIT ---
echo -e "\n🔒 [3/4] AUDITING EXECUTION BITS..."
ls -l "$TARGET"

# --- 4. PREPARED SED INJECTIONS FOR AUTOMATED REPAIRS ---
echo -e "\n🛠️ [4/4] REMEDIATION SUGGESTIONS (UNCOMMENT TO APPLY)..."

# Repair 1: Convert Windows CRLF (\r\n) to Unix LF (\n)
# sed -i 's/\r$//' repositories/fluid_dynamics_simulator/setup_scripts/mesh_gen_setup.sh

# Repair 2: Force execution permissions
# chmod +x repositories/fluid_dynamics_simulator/setup_scripts/mesh_gen_setup.sh

# Repair 3: Remove Byte Order Mark (BOM) if present
# sed -i '1s/^\xef\xbb\xbf//' repositories/fluid_dynamics_simulator/setup_scripts/mesh_gen_setup.sh

echo "========================================================================"
echo "🏁 AUDIT COMPLETED. IF OUTPUT ABOVE SHOWS 'CRLF' OR '^M', USE REPAIR 1. 🏁"
echo "========================================================================"