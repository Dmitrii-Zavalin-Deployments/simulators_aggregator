#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Diagnostic: Locating test cases and root-cause functions ==="
grep -n -C 8 "test_main_complete_success_flow" tests/pipeline/test_provision_environment.py || true
grep -n -C 5 "test_main_corrupt_json_format" tests/pipeline/test_provision_environment.py || true
grep -n -C 5 "subprocess.run" src/pipeline/provision_environment.py || true
grep -n -C 5 "json.load" src/pipeline/provision_environment.py || true

echo "=== 2. Smoking-gun source audit using cat -n ==="
if [ -f "src/pipeline/provision_environment.py" ]; then
    echo "--- src/pipeline/provision_environment.py ---"
    cat -n src/pipeline/provision_environment.py
fi

if [ -f "tests/pipeline/test_provision_environment.py" ]; then
    echo "--- tests/pipeline/test_provision_environment.py ---"
    cat -n tests/pipeline/test_provision_environment.py
fi

echo "=== 3. Automated Repair Injections (commented with # as requested) ==="
# Repair 1: Catch generic Exception alongside JSONDecodeError and OSError during task.json parsing
# sed -i 's/except (json.JSONDecodeError, OSError) as e:/except (json.JSONDecodeError, OSError, Exception) as e:/g' src/pipeline/provision_environment.py

# Repair 2: Prevent unwanted repo deletion / ensure correct mock path returns in test_main_complete_success_flow
# sed -i 's/mock_exists.return_value = True/mock_exists.side_effect = lambda path: "task.json" in str(path) or ".git" in str(path)/g' tests/pipeline/test_provision_environment.py

echo "=== 4. Re-running target test suite for verification ==="
# pytest tests/pipeline/test_provision_environment.py || true