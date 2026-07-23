#!/usr/bin/env bash
set -euo pipefail

echo "================================================================="
echo "🛠️ APPLYING COMPLETE COMPILER REPAIRS & RUFF FIXES"
echo "================================================================="

# 1. Fix EXE001: Grant execution permissions to script files with shebangs
chmod +x src/io/upload_to_dropbox.py \
         src/pipeline/initialize_workspace.py \
         src/pipeline/matrix_exploder.py \
         src/pipeline/provision_environment.py \
         src/pipeline/record_telemetry.py \
         src/pipeline/unified_orchestrator.py

# 2. Fix TRY201: Replace 'raise e' with clean 'raise'
sed -i 's/raise e$/raise/' src/io/state_manager.py

# 3. Fix DTZ003: Modernize timezone-aware UTC datetime
sed -i 's/datetime\.datetime\.utcnow()/datetime.datetime.now(datetime.timezone.utc)/' src/pipeline/record_telemetry.py
grep -q "from datetime import timezone" src/pipeline/record_telemetry.py || \
sed -i 's/import datetime/import datetime\nfrom datetime import timezone/' src/pipeline/record_telemetry.py

# 4. Fix BLE001: Add inline suppression for valid CLI top-level exception handlers
sed -i 's/except Exception as e:/except Exception as e:  # noqa: BLE001/' src/io/state_manager.py
sed -i 's/except Exception as e:/except Exception as e:  # noqa: BLE001/' src/io/download_from_dropbox.py
sed -i 's/except Exception as e:/except Exception as e:  # noqa: BLE001/' src/io/upload_to_dropbox.py
sed -i 's/except Exception as e:/except Exception as e:  # noqa: BLE001/' src/pipeline/provision_environment.py
sed -i 's/except Exception as e:/except Exception as e:  # noqa: BLE001/' src/pipeline/unified_orchestrator.py

# 5. Fix RUF023: Sort __slots__ alphabetically in tuner_state.py
python3 -c '
path = "src/state/tuner_state.py"
with open(path, "r") as f:
    content = f.read()
old_slots = """__slots__ = [
        # --- Unified Fields (Input Schema & Output Task Schema) ---
        '\''pipeline_id'\'',              # Identifier for the target YAML/JSON in Library
        '\''steps'\'',                    # Sequential pipeline step routing mapping
        
        # --- Provenance & Environment Traceability (The BOM) ---
        '\''task_details'\'',             # Immutable manifest of repo/setup state (tracking everything)
        
        # --- Output Schema Deliverables ---
        '\''successful_runs_archive'\'',  # Target folder name for successful execution results
        '\''failed_runs_archive'\'',      # Target folder name for failed execution results
    ]"""
new_slots = """__slots__ = [
        "failed_runs_archive",
        "pipeline_id",
        "steps",
        "successful_runs_archive",
        "task_details",
    ]"""
content = content.replace(old_slots, new_slots)
with open(path, "w") as f:
    f.write(content)
'

# 6. Fix PLW1510: Add explicit check=False to subprocess.run calls
sed -i 's/result = subprocess.run(clone_cmd)/result = subprocess.run(clone_cmd, check=False)/' src/pipeline/provision_environment.py

python3 -c '
path = "src/pipeline/unified_orchestrator.py"
with open(path, "r") as f:
    content = f.read()
content = content.replace(
    "result = subprocess.run(\n                run_cmd,",
    "result = subprocess.run(\n                run_cmd,\n                check=False,"
)
with open(path, "w") as f:
    f.write(content)
'

# 7. Fix SIM103: Inline conditional return in test_unified_orchestrator.py
python3 -c '
path = "tests/pipeline/test_unified_orchestrator.py"
with open(path, "r") as f:
    content = f.read()
old_block = """          def existence_router(path_obj=None, *args, **kwargs):
              path_str = str(path_obj)
              if "sim-engine" in path_str:
                  return False  # Force missing repository to trigger clone step
              return True       # Keep core setup blueprints active"""
new_block = """          def existence_router(path_obj=None, *args, **kwargs):
              path_str = str(path_obj)
              return "sim-engine" not in path_str"""
content = content.replace(old_block, new_block)
with open(path, "w") as f:
    f.write(content)
'

# 8. Execute automated Ruff fixes (SIM117, RUF015, etc.)
ruff check src tests --fix --unsafe-fixes

echo "================================================================="
echo "✅ ALL REPAIRS COMPLETED. RUNNING FINAL LINT CHECK..."
echo "================================================================="
ruff check src tests