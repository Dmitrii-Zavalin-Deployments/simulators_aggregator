import json
from typing import Any


class TunerState:
    """
    Sovereign Container: The single source of truth for the ACE Pipeline.
    Enforces a strict Zero-Default Policy with structural initialization.
    """
    __slots__ = [
        'failed_runs_archive',      # Target folder name for failed execution results
        'pipeline_id',              # Identifier for the target YAML/JSON in Library
        'steps',                    # Sequential pipeline step routing mapping
        'successful_runs_archive',  # Target folder name for successful execution results
        'task_details',             # Immutable manifest of repo/setup state (tracking everything)
    ]

    def __init__(
        self, 
        pipeline_id: str, 
        steps: dict[str, dict[str, str]],
        task_details: list[dict[str, Any]],
        successful_runs_archive: str,
        failed_runs_archive: str
    ):
        # --- Zero-Default Policy Verification ---
        if pipeline_id is None:
            raise ValueError("Missing structural parameter: pipeline_id")
        if steps is None:
            raise ValueError("Missing structural parameter: steps")
        if task_details is None:
            raise ValueError("Missing structural parameter: task_details")
        if successful_runs_archive is None:
            raise ValueError("Missing structural parameter: successful_runs_archive")
        if failed_runs_archive is None:
            raise ValueError("Missing structural parameter: failed_runs_archive")

        # --- Deep Structural Validation for Steps Map ---
        if not isinstance(steps, dict):
            raise TypeError("Structural parameter 'steps' must be a dictionary mapping.")
        
        required_step_fields = {"input_file_name", "output_file_name", "input_output_folder"}
        for step_key, step_meta in steps.items():
            if not isinstance(step_meta, dict):
                raise TypeError(f"Step metadata for key '{step_key}' must be a dictionary configuration.")
            
            missing_fields = required_step_fields - step_meta.keys()
            if missing_fields:
                raise ValueError(
                    f"Step '{step_key}' violates validation schema. Missing required fields: {list(missing_fields)}"
                )
            
            # Ensure none of the values are null or empty strings
            for field in required_step_fields:
                if not step_meta[field]:
                    raise ValueError(f"Step '{step_key}' field '{field}' cannot be empty or null.")

        # Assign properties to state container instance
        self.pipeline_id = pipeline_id
        self.steps = steps
        self.task_details = task_details
        self.successful_runs_archive = successful_runs_archive
        self.failed_runs_archive = failed_runs_archive

    # --- Dehydration & Hydration Logic ---

    def to_dict(self) -> dict[str, Any]:
        """Converts state to flat dictionary schema mapping for persistent serialization."""
        return {slot: getattr(self, slot) for slot in self.__slots__}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TunerState':
        """Reconstructs state with validation checks ensuring no optional fallbacks exist."""
        for slot in cls.__slots__:
            if slot not in data:
                raise KeyError(f"Critical State Corruption: Missing mandated state property '{slot}' during Hydration.")
        
        return cls(
            pipeline_id=data['pipeline_id'],
            steps=data['steps'],
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

    def to_saap_deliverable(self) -> dict[str, Any]:
        """
        Transforms Sovereign Container properties into a nested dictionary
        perfectly matching the structural constraints of Tuner Output Schema.
        """
        return {
            "task": {
                "pipeline_id": self.pipeline_id,
                "steps": self.steps,
                "task_details": self.task_details
            },
            "deliverables": {
                "successful_runs_archive": self.successful_runs_archive,
                "failed_runs_archive": self.failed_runs_archive,
            }
        }