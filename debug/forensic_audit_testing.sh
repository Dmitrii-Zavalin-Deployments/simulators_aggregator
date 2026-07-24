#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Diagnostic: Locating with-blocks and indentation in test files ==="
grep -n -C 5 "with caplog.at_level" tests/pipeline/test_matrix_exploder_1.py tests/pipeline/test_record_telemetry.py || true

echo "=== 2. Smoking-gun source audit using cat -n ==="
echo "--- tests/pipeline/test_matrix_exploder_1.py (lines 55 to 85) ---"
sed -n '55,85p' tests/pipeline/test_matrix_exploder_1.py | cat -n

echo "--- tests/pipeline/test_record_telemetry.py (lines 20 to 40) ---"
sed -n '20,40p' tests/pipeline/test_record_telemetry.py | cat -n

echo "=== 3. Executing Automated Indent Repair ==="
python3 -c '
import re

files = [
    "tests/pipeline/test_matrix_exploder_1.py",
    "tests/pipeline/test_record_telemetry.py"
]

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Target pattern: fix blocks where with statements and their contents lack proper nesting indentation
    # We ensure lines inside test functions under `with caplog...` blocks are properly indented.
    lines = content.splitlines(keepends=True)
    new_lines = []
    in_target_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "def test_main_" in stripped:
            in_target_block = True
            new_lines.append(line)
            continue
            
        if in_target_block:
            # Fix patch continuation lines or inner with/assert statements under caplog blocks
            if stripped.startswith("patch(") and line.startswith("    "):
                new_lines.append("        " + stripped + "\n")
            elif (stripped.startswith("# We expect") or stripped.startswith("# Verify") or stripped.startswith("# Execute") or stripped.startswith("# The system")) and line.startswith("    "):
                new_lines.append("    " + line)
            elif (stripped.startswith("with pytest.raises") or stripped.startswith("matrix_exploder.") or stripped.startswith("record_telemetry.") or stripped.startswith("assert ")) and line.startswith("    "):
                # If it is directly under a with statement, it needs 8 spaces indentation
                new_lines.append("        " + stripped + "\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(filepath, "w") as f:
        f.writelines(lines)

print("Automated repair pass completed.")
'

echo "=== 4. Verifying Syntax with Ruff ==="