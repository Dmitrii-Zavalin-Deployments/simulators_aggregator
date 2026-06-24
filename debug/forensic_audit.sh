#!/bin/bash
# src/debug/forensic_audit.sh
# Integrity Auditor: Confirms environment consistency and verifies generated state artifacts.

echo "🔍 --- STARTING INTEGRITY AUDIT ---"

# 1. CONDA VALIDATION
echo -e "\n🧩 --- CONDA ENVIRONMENT ---"
if conda list pythonocc-core | grep -q "pythonocc-core"; then
    echo "✅ pythonocc-core is installed."
    conda list pythonocc-core | grep pythonocc-core
else
    echo "❌ CRITICAL: pythonocc-core is MISSING."
    exit 1
fi

# 2. PIP DEPENDENCY VALIDATION
echo -e "\n📦 --- PIP PACKAGE VALIDATION ---"
REQUIRED_PKGS=("numpy" "h5py" "requests" "jsonschema")

for pkg in "${REQUIRED_PKGS[@]}"; do
    if pip show "$pkg" > /dev/null 2>&1; then
        echo "✅ $pkg is installed:"
        pip show "$pkg" | grep -E "Name:|Version:"
    else
        echo "❌ CRITICAL: $pkg is MISSING."
        exit 1
    fi
done

# 3. INTEGRITY CHECK
echo -e "\n🛡️ --- DEPENDENCY INTEGRITY CHECK ---"
if pip check; then
    echo "✅ No dependency conflicts found."
else
    echo "⚠️ WARNING: Potential dependency conflicts detected."
fi

# 4. SOVEREIGN STATE VERIFICATION
echo -e "\n📂 --- SOVEREIGN STATE VERIFICATION ---"
BRANCH="${GITHUB_REF_NAME:-main}"
STATE_DIR="data/testing-input-output/tuning_${BRANCH}"

if [ -d "$STATE_DIR" ]; then
    echo "📍 Verifying contents of workspace: $STATE_DIR"
    
    # List the tree
    echo -e "\n--- RECURSIVE DIRECTORY LISTING (ls -R) ---"
    ls -R "$STATE_DIR"
    
    # Automatically cat all JSON files found in the directory tree
    echo -e "\n--- DUMPING CONTENT OF ALL JSON ASSETS ---"
    find "$STATE_DIR" -type f -name "*.json" | while read -r json_file; do
        echo -e "\n========================================="
        echo "FILE: $json_file"
        echo "========================================="
        cat "$json_file"
    done
    
    # Verify critical file existence
    if [ ! -f "$STATE_DIR/state.json" ]; then
        echo -e "\n❌ ERROR: state.json was NOT found."
        exit 1
    fi
else
    echo "❌ ERROR: State directory $STATE_DIR does not exist."
    exit 1
fi

echo -e "\n✅ --- INTEGRITY AUDIT COMPLETE ---"