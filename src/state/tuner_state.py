# src/state/tuner_state.py
import json
from typing import List, Dict, Any

class TunerState:
    """
    Sovereign Container: The single source of truth for the ACE Pipeline.
    Enforces a strict Zero-Default Policy with structural initialization.
    """
    __slots__ = [
        # --- Unified Fields (Input Schema & Output Task Schema) ---
        'pipeline_id',              # Identifier for the target YAML/JSON in Library
        'input_data_list',          # The list of names of the input files for this run
        
        # --- Provenance & Environment Traceability (The BOM) ---
        'task_details',             # Immutable manifest of repo/setup state (tracking everything)
        
        # --- Output Schema Deliverables ---
        'successful_runs_archive',  # Target folder name for successful execution results
        'failed_runs_archive',      # Target folder name for failed execution results
    ]

    def __init__(
        self, 
        pipeline_id: str, 
        input_data_list: List[str],
        task_details: List[Dict[str, Any]],
        successful_runs_archive: str,
        failed_runs_archive: str
    ):
        # --- Zero-Default Policy Verification ---
        if pipeline_id is None: raise ValueError("Missing structural parameter: pipeline_id")
        if input_data_list is None: raise ValueError("Missing structural parameter: input_data_list")
        if task_details is None: raise ValueError("Missing structural parameter: task_details")
        if successful_runs_archive is None: raise ValueError("Missing structural parameter: successful_runs_archive")
        if failed_runs_archive is None: raise ValueError("Missing structural parameter: failed_runs_archive")

        # Assign properties to state container instance
        self.pipeline_id = pipeline_id
        self.input_data_list = input_data_list
        self.task_details = task_details
        self.successful_runs_archive = successful_runs_archive
        self.failed_runs_archive = failed_runs_archive

    # --- Dehydration & Hydration Logic ---

    def to_dict(self) -> Dict[str, Any]:
        """Converts state to flat dictionary schema mapping for persistent serialization."""
        return {slot: getattr(self, slot) for slot in self.__slots__}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TunerState':
        """Reconstructs state with validation checks ensuring no optional fallbacks exist."""
        for slot in cls.__slots__:
            if slot not in data:
                raise KeyError(f"Critical State Corruption: Missing mandated state property '{slot}' during Hydration.")
        
        return cls(
            pipeline_id=data['pipeline_id'],
            input_data_list=data['input_data_list'],
            task_details=data['task_details'],
            successful_runs_archive=data['successful_runs_archive'],
            failed_runs_archive=data['failed_runs_archive'],
        )

    def save_to_disk(self, path: str):
        """Atomic write step to serialize State Machine data plane parameters to disk."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load_from_disk(cls, path: str) -> 'TunerState':
        """Hydration entrypoint reading strictly from state configuration outputs."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    # --- Output Compliance (SaaP Deliverable Validation) ---

    def to_saap_deliverable(self) -> Dict[str, Any]:
        """
        Transforms Sovereign Container properties into a nested dictionary
        perfectly matching the structural constraints of Tuner Output Schema.
        """
        return {
            "task": {
                "pipeline_id": self.pipeline_id,
                "input_data_list": self.input_data_list,
                "task_details": self.task_details
            },
            "deliverables": {
                "successful_runs_archive": self.successful_runs_archive,
                "failed_runs_archive": self.failed_runs_archive,
            }
        }