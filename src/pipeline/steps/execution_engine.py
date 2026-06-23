import time
from typing import Dict, Any
from interfaces.step_interface import StepInterface
from src.state.tuner_state import TunerState

# --- External Helper (Preserves Class Constitution) ---
def run_module_simulation(module_name: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refactored from the 'solve()' dummy in test_integrations.py.
    Executes a single step in the pipeline.
    """
    start_time = time.time()
    try:
        # Explicit Zero-Default check
        if not config_data:
            raise ValueError(f"CRITICAL: No config provided for module '{module_name}'")
        
        # [Simulated Physics Execution Time]
        time.sleep(0.1) 
        
        return {
            "status": "SUCCESS", 
            "execution_time": time.time() - start_time
        }
    except Exception as e:
        return {
            "status": "FAILED", 
            "error_log": str(e), 
            "execution_time": time.time() - start_time
        }


class ExecutionEngineStep(StepInterface):
    """
    Executes the ACE (Automated Cumulative Execution) Loop.
    Pulls a batch from the Sovereign Container and applies depth-first branch pruning.
    """
    
    def execute(self, container: TunerState) -> None:
        # Configure the hourly pulse limit (e.g., 10 permutations per run)
        BATCH_LIMIT = 10 
        
        # 1. Retrieve the exact slice from the Super-Matrix using the bookmark cursor
        batch = container.get_next_batch(BATCH_LIMIT)
        if not batch:
            return 

        # 2. The ACE Loop
        for permutation in batch:
            pipeline_status = "SUCCESS"
            total_time = 0.0
            failed_at = None
            error_message = None

            # Execute modules sequentially (Depth-First)
            for module_name, config_data in permutation.items():
                result = run_module_simulation(module_name, config_data)
                total_time += result["execution_time"]

                # Branch Pruning (Fail-Fast)
                if result["status"] == "FAILED":
                    pipeline_status = "FAILED"
                    failed_at = module_name
                    error_message = result.get("error_log")
                    break 

            # 3. Log Results deterministically to the Sovereign Container
            permutation_id = f"run_{hash(str(permutation))}" # Unique ID

            if pipeline_status == "SUCCESS":
                container.successful_runs.append({
                    "permutation_id": permutation_id,
                    "status": "SUCCESS",
                    "pipeline_configs": permutation,
                    "execution_time_total": total_time
                })
            else:
                container.failed_runs.append({
                    "permutation_id": permutation_id,
                    "status": "FAILED",
                    "failed_at": failed_at,
                    "pipeline_configs": permutation,
                    "error_log": error_message
                })
        
        # 4. Advance the State Machine cursor
        container.advance_cursor(len(batch))