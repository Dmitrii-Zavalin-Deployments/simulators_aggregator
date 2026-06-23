from typing import List, Dict, Any, Protocol

class PipelineInterface(Protocol):
    """
    Composite read-only interface for the final global pipeline state.
    Acts as the strict architectural Exit Gate for validation verification loops.
    """

    @property
    def pipeline_id(self) -> str:
        """Accesses the verified tracking string identifier of the executing pipeline."""
        ...

    @property
    def total_permutations(self) -> int:
        """Returns the total number of evaluation targets generated in the multi-module search space."""
        ...

    @property
    def remaining_permutations(self) -> int:
        """Calculates the count of pending permutations remaining based on current cursor pointer positioning."""
        ...

    @property
    def active_batch_slice(self) -> List[Dict[str, Any]]:
        """Returns a snapshot slice of configuration arrays allocated for the current active pulse run."""
        ...

    @property
    def current_success_manifest(self) -> List[Dict[str, Any]]:
        """Exposes a read-only list of completed, verified full-chain module tracking logs."""
        ...

    @property
    def current_failure_manifest(self) -> List[Dict[str, Any]]:
        """Exposes a read-only list of short-circuited failed run logs along with forensic bottleneck markers."""
        ...

    @property
    def local_workspace_paths(self) -> Dict[str, str]:
        """Exposes the routing absolute target values mapped for local compression handling and staging layers."""
        ...