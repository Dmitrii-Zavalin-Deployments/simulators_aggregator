#!/usr/bin/env bash
# src/debug/forensic_audit.sh
# 🔍 Post-Mortem Diagnostic Audit for Git Protocol Mismatch (SSH vs HTTPS)

set -u  # Treat unset variables as an error

echo "========================================================================="
echo "🔍 STARTING FORENSIC INTEGRITY AUDIT: GIT PROTOCOL DISCOVERY"
echo "========================================================================="

# --- Step 1: Grep / Cat Diagnostics for Code/Output Root Causes ---
echo -e "\n🕵️ STEP 1: Analysing State Repository Schemas..."
if [ -f "data/testing-input-output/tuning_main/state.json" ]; then
    echo "📄 Target manifest discovered. Extracting defined repository endpoints:"
    grep -n "repository_url" data/testing-input-output/tuning_main/state.json
else
    echo "⚠️ Warning: data/testing-input-output/tuning_main/state.json not initialized yet."
fi

# --- Step 2: Smoking-Gun Source Audits (Line-Numbered) ---
echo -e "\n🔥 STEP 2: Line-Numbered Source Audit of Batch Executor Git Interface..."
if [ -f "src/pipeline/execute_batch.py" ]; then
    echo "--- [SOURCE VIEW] src/pipeline/execute_batch.py ---"
    # Isolate the exact runtime block where git clone operations are constructed
    cat -n src/pipeline/execute_batch.py | grep -B 5 -A 10 "git clone"
else
    echo "❌ CRITICAL ERROR: src/pipeline/execute_batch.py does not exist."
fi

# --- Step 3: Root Cause Analysis ---
echo -e "\n💡 ROOT CAUSE ANALYSIS:"
echo "The target repository uses an SSH string format ('git@github.com:'). Even if a repository"
echo "is public, git forces SSH key authentication when this protocol is invoked. Because the"
echo "GitHub Actions runner lacks an explicit SSH deployment key, it drops connection with a 'Permission denied'."
echo "Fix: Translate the SSH endpoint dynamically to HTTPS ('https://github.com/') inside the loop."

# --- Step 4: Automated Sed Injection Repair Blueprints ---
echo -e "\n🛡️ STEP 4: Automated sed Repair Blueprints (Commented for Automation Triggering)..."
echo "Run the specific sed injection matching your workspace pattern to normalize git endpoints:"

# Scenario A: Inline protocol normalization right before the subprocess execution block
# sed -i '/git clone {repo_url}/i \            if repo_url.startswith("git@github.com:"): repo_url = repo_url.replace("git@github.com:", "https://github.com/")' src/pipeline/execute_batch.py

# Scenario B: Overwriting baseline configuration manifests directly via stream processing
# sed -i 's/git@github.com:/https:\/\/github.com\//g' data/testing-input-output/tuning_main/state.json

echo -e "\n========================================================================="
echo "✅ FORENSIC INTEGRITY AUDIT COMPLETE"
echo "========================================================================="