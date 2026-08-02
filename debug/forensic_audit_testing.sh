#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "DIAGNOSTICS: Inspecting test failure root causes"
echo "=========================================="
echo "--- Checking how state_status is asserted in tests ---"
grep -n "state_status" tests/io/test_state_manager.py || true

echo "--- Checking exception handling and excepthook implementation ---"
grep -n -C 5 "excepthook" src/io/state_manager.py || true

echo ""
echo "=========================================="
echo "SMOKING-GUN SOURCE AUDIT: src/io/state_manager.py"
echo "=========================================="
cat -n src/io/state_manager.py

echo ""
echo "=========================================="
echo "AUTOMATED REPAIRS (SED INJECTIONS)"
echo "=========================================="
# Fix 1: Restore plain print statements for state signals so capsys captures exact strings ('state_status=found' / 'state_status=not_found')
# sed -i 's/logger.info("state_status=/print("state_status=/g' src/io/state_manager.py

# Fix 2: Remove custom sys.excepthook interception so unit tests can directly catch expected exceptions (OSError/Exception) instead of receiving SystemExit
# sed -i '/def handle_exception/,+6d' src/io/state_manager.py
# sed -i '/sys.excepthook = handle_exception/d' src/io/state_manager.py
# sed -i 's/logger.error(f"CRITICAL ERROR: {exc_value}")/print(f"CRITICAL ERROR: {exc_value}", file=sys.stderr)/g' src/io/state_manager.py