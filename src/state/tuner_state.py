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
        'successful_runs_archive',  # Filename of the successful runs ZIP (e.g., successful_runs_<branch>.zip)
        'failed_runs_archive',      # Filename of the failed runs ZIP (e.g., failed_runs_<branch>.zip)
        'saap_skeleton',            # Path to the root of the generated saap_skeleton folder structure
        
        # --- Explicitly Requested Path Routing Slots ---
        'saap_skeleton_path',       # Explicit absolute/relative path to the saap skeleton workspace
        'success_zip_path',         # Explicit path routing for local compression handling of successful runs
        'failed_zip_path',          # Explicit path routing for local compression handling of failed runs
        
        # --- Operational Automated Cumulative Execution (ACE) Tracking State ---
        'combinations_to_test',     # The complete multi-module structural search space (Super-Matrix)
        'successful_runs',          # Collection of individual run data payloads matching Tuner Results Schema
        'failed_runs',              # Collection of individual run error payloads matching Tuner Results Schema
        'batch_cursor'              # Tracks progress for the Pulsed Batch execution cursor index
    ]

    def __init__(
        self, 
        pipeline_id: str, 
        input_data_list: List[str],
        task_details: List[Dict[str, Any]],
        successful_runs_archive: str,
        failed_runs_archive: str,
        saap_skeleton: str,
        saap_skeleton_path: str,
        success_zip_path: str,
        failed_zip_path: str,
        combinations_to_test: List[Dict[str, Any]],
        successful_runs: List[Dict[str, Any]],
        failed_runs: List[Dict[str, Any]],
        batch_cursor: int
    ):
        # --- Zero-Default Policy Verification ---
        if pipeline_id is None: raise ValueError("Missing structural parameter: pipeline_id")
        if input_data_list is None: raise ValueError("Missing structural parameter: input_data_list")
        if task_details is None: raise ValueError("Missing structural parameter: task_details")
        if successful_runs_archive is None: raise ValueError("Missing structural parameter: successful_runs_archive")
        if failed_runs_archive is None: raise ValueError("Missing structural parameter: failed_runs_archive")
        if saap_skeleton is None: raise ValueError("Missing structural parameter: saap_skeleton")
        if saap_skeleton_path is None: raise ValueError("Missing structural parameter: saap_skeleton_path")
        if success_zip_path is None: raise ValueError("Missing structural parameter: success_zip_path")
        if failed_zip_path is None: raise ValueError("Missing structural parameter: failed_zip_path")
        if combinations_to_test is None: raise ValueError("Missing structural parameter: combinations_to_test")
        if successful_runs is None: raise ValueError("Missing structural parameter: successful_runs")
        if failed_runs is None: raise ValueError("Missing structural parameter: failed_runs")
        if batch_cursor is None: raise ValueError("Missing structural parameter: batch_cursor")

        # Assign properties to state container instance
        self.pipeline_id = pipeline_id
        self.input_data_list = input_data_list
        self.task_details = task_details
        self.successful_runs_archive = successful_runs_archive
        self.failed_runs_archive = failed_runs_archive
        self.saap_skeleton = saap_skeleton
        self.saap_skeleton_path = saap_skeleton_path
        self.success_zip_path = success_zip_path
        self.failed_zip_path = failed_zip_path
        self.combinations_to_test = combinations_to_test
        self.successful_runs = successful_runs
        self.failed_runs = failed_runs
        self.batch_cursor = batch_cursor

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
            saap_skeleton=data['saap_skeleton'],
            saap_skeleton_path=data['saap_skeleton_path'],
            success_zip_path=data['success_zip_path'],
            failed_zip_path=data['failed_zip_path'],
            combinations_to_test=data['combinations_to_test'],
            successful_runs=data['successful_runs'],
            failed_runs=data['failed_runs'],
            batch_cursor=data['batch_cursor']
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
                "task_details": self.task_details # Added to deliverable
            },
            "deliverables": {
                "successful_runs_archive": self.successful_runs_archive,
                "failed_runs_archive": self.failed_runs_archive,
                "saap_skeleton": self.saap_skeleton
            }
        }

    # --- Pulsed Batch Utilities ---

    def get_next_batch(self, limit: int) -> List[Dict[str, Any]]:
        """Slices the search space from the bookmark array pointer location."""
        start = self.batch_cursor
        end = min(start + limit, len(self.combinations_to_test))
        return self.combinations_to_test[start:end]

    def advance_cursor(self, batch_size: int):
        """Advances pointer cleanly upon conclusion of automated batch cycle."""
        self.batch_cursor += batch_size