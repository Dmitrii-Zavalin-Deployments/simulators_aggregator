#!/usr/bin/bash
set -euo pipefail

echo "========================================================================"
echo "🔍 ACE LOOP FORENSIC AUDIT: DIAGNOSING WORKSPACE REBASE LOCKS"
echo "========================================================================"

# 1️⃣ DIAGNOSTICS: Locate the hidden unstaged changes blocking the rebase
echo "📋 [DIAGNOSTIC] Inspecting raw porcelain workspace drift..."
git status --porcelain

echo -e "\n📋 [DIAGNOSTIC] Tracked files with unstaged modifications:"
git diff --name-only

# 2️⃣ SMOKING-GUN SOURCE AUDIT: Check the exact composition of the files
echo -e "\n🔬 [AUDIT] Auditing ledger state and local tracking files..."
if [ -f "performance_audit.md" ]; then
    echo "📄 Top lines of performance_audit.md:"
    cat -n performance_audit.md | head -n 25
else
    echo "⚠️ performance_audit.md not found in root context."
fi

# 3️⃣ RECONNAISSANCE: Grep for specific automated triggers
echo -e "\n🧠 [ANALYSIS] Checking for blocking structural conditions..."
git status | grep -E "Changes not staged|Untracked files" || echo "✅ Workspace cleanly evaluated by core checks."

echo "========================================================================"
echo "🛠️ AUTOMATED REPAIRS (PROPOSED INJECTIONS)"
echo "========================================================================"
echo "The Fix: The inline YAML runner must stash ALL tracked workspace mutations"
echo "(including flags and forensic scripts) to allow an uninhibited rebase pull."
echo "Uncomment the following lines in your generation context to apply fixes:"

# sed -i 's/git stash push -m "temporary-automation-isolation" performance_audit.md/git stash push --include-untracked -m "temporary-automation-isolation"/g' .github/workflows/your_workflow.yml
# sed -i 's/git add performance_audit.md/git add -A/g' .github/workflows/your_workflow.yml

echo "💡 Forensic run finished."