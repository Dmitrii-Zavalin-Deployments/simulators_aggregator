#!/bin/bash
# src/debug/forensic_audit.sh
# Integrity Auditor: Confirms the environment is consistent post-setup.

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
# pip check ensures that the installed packages have compatible dependencies
if pip check; then
    echo "✅ No dependency conflicts found."
else
    echo "⚠️ WARNING: Potential dependency conflicts detected above."
fi

echo -e "\n✅ --- INTEGRITY AUDIT COMPLETE ---"