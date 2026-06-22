# src/core/constants.py

from enum import Enum

class OrchestrationStatus(Enum):
    """
    The Operational Truth for Nomadic Workflows.
    Logic is driven by physical artifact presence in 'data/testing-input-output/'.
    
    Transition Matrix Mapping:
    - WAITING: Artifacts missing (Inputs).
    - PENDING: Artifacts present (Inputs), ready to fire.
    - IN_PROGRESS: Dispatched, awaiting Results (Outputs).
    - COMPLETED: Artifacts verified (Outputs).
    - FAILED: Temporal breach (Timeout).
    """
    WAITING = "WAITING"         # Input artifacts missing; blocked by upstream
    PENDING = "PENDING"         # Inputs present; ready for dispatch
    IN_PROGRESS = "IN_PROGRESS" # Triggered; awaiting output artifact
    COMPLETED = "COMPLETED"     # Output artifact verified on disk
    FAILED = "FAILED"           # Timeout exceeded; requires automated reset

class SystemPaths:
    """
    Standardized internal relative paths for the nomadic engine.
    """
    CONFIG_DIR = "config"
    SCHEMA_DIR = "schema"  # New Directory
    DATA_DIR = "data/testing-input-output"
    
    # Files
    ACTIVE_DISK = "active_disk.json"
    LEDGER = "orchestration_ledger.json"
    DORMANT_FLAG = "dormant.flag"
    
    # Schemas
    MANIFEST_SCHEMA = "manifest_schema.json"
    ACTIVE_DISK_SCHEMA = "active_disk_schema.json"