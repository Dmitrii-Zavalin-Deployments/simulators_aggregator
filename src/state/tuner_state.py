from typing import List, Dict, Any, TypeAlias

# Define the manifest type for clarity
ConfigManifest: TypeAlias = Dict[str, Any]

class TunerState:
    """
    Sovereign Container: The single source of truth for the Tuner.
    """
    __slots__ = [
        'pipeline_id', 'config_ids', 'input_data_list', 
        'library_path', 'combinations_to_test', 
        'successful_runs', 'failed_runs',
        'saap_skeleton_path', 'success_zip_path', 'failed_zip_path'
    ]

    def __init__(
        self, 
        pipeline_id: str, 
        config_ids: List[str], 
        input_data_list: List[str],
        library_path: str
    ):
        # ... (your existing validation logic) ...
        self.pipeline_id = pipeline_id
        self.config_ids = config_ids
        self.input_data_list = input_data_list
        self.library_path = library_path
        
        # Manifests and Results
        self.combinations_to_test: List[ConfigManifest] = []
        self.successful_runs: List[ConfigManifest] = []
        self.failed_runs: List[ConfigManifest] = []
        
        # Paths
        self.saap_skeleton_path: str = ""
        self.success_zip_path: str = ""
        self.failed_zip_path: str = ""