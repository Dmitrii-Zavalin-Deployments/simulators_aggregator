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

# Ensure datetime.timezone is imported in record_telemetry.py if missing
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

# 6. Execute automated Ruff unsafe fixes for SIM117, SIM103, RUF015, and PLW1510
ruff check src tests --fix --unsafe-fixes

ruff check src tests