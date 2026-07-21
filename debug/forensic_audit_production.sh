#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "       DORMANT FLAG FORENSIC AUDIT SCRIPT         "
echo "=================================================="

# 1. Check current state and metadata of local dormant.flag
echo "--- [1] Checking local 'dormant.flag' file status ---"
if [ -f "dormant.flag" ]; then
    echo "✅ File exists. Content:"
    cat -A dormant.flag
    echo "📂 File metadata:"
    ls -l dormant.flag
else
    echo "⚠️ Notice: 'dormant.flag' does not currently exist in the working directory."
fi

# 2. Trace Git history to see who or what commit modified the flag last
echo -e "\n--- [2] Tracing Git History & Commit Changes for 'dormant.flag' ---"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Recent commits touching dormant.flag:"
    git log -n 5 --oneline --follow -- dormant.flag || echo "No git history found for dormant.flag."
    
    echo -e "\nLast modification diff:"
    git log -n 1 -p -- dormant.flag || echo "No diff available."
else
    echo "⚠️ Not inside a Git repository."
fi

# 3. Scan codebase for any script or workflow writing to dormant.flag
echo -e "\n--- [3] Scanning codebase for 'dormant.flag' interactions ---"
echo "Searching in src/ and .github/workflows/ for flag references:"
grep -rn "dormant.flag" src/ .github/workflows/ || echo "No direct string matches found."

# 4. Search for hardcoded status strings
echo -e "\n--- [4] Scanning for hardcoded 'STATUS: DORMANT' assignments ---"
grep -rn "STATUS: DORMANT" src/ .github/workflows/ || echo "No hardcoded DORMANT strings found."

echo "=================================================="
echo "       AUDIT SCRIPT COMPLETED SUCCESSFULLY        "
echo "=================================================="