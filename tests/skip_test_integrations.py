import json
import os
import time
from tests.dummies import dummy_in, dummy_out

# --- 1. The Execution Engine (The Tuner) ---
def solve(task: dummy_in, config_id: str) -> dummy_out:
    result = dummy_out()
    start_time = time.time()
    try:
        if not hasattr(task, 'input_data_list') or not task.input_data_list:
            raise ValueError("No input data provided")
        
        time.sleep(0.1) 
        
        result.override(
            status="success",
            module_output=f"output_{task.pipeline_id}_{config_id}.zip"
        )
    except Exception as e:
        result.override(status="failed", error_log=str(e))
    
    result.override(execution_time_seconds = time.time() - start_time)
    return result

# --- 2. The Packaging Engine (The Aggregator) ---
def package_output(results_data: dict):
    os.makedirs('successful_runs', exist_ok=True)
    os.makedirs('failed_runs', exist_ok=True)
    os.makedirs('saap_skeleton/configs', exist_ok=True)

    for run in results_data['results']:
        run_id = run['run_id']
        folder = 'successful_runs' if run['status'] == 'success' else 'failed_runs'
        filename = f"{folder}/{run_id}.json"
        with open(filename, 'w') as f:
            json.dump(run, f, indent=4)

    with open('saap_skeleton/pipeline.yml', 'w') as f:
        f.write("# Placeholder for library pipeline file")

# --- 3. THE INTEGRATION TEST HARNESS ---
if __name__ == "__main__":
    print("--- Starting Integration Discovery Test ---")

    # A. Setup
    task_success = dummy_in(pipeline_id="thermal_v1", input_data_list=["data.csv"])
    task_fail = dummy_in(pipeline_id="thermal_v1", input_data_list=[])

    # B. Run Tuner Engine
    results_list = []
    
    res1 = solve(task_success, "config_001")
    results_list.append({"run_id": "run_001", "status": res1.status, "execution_time_seconds": res1.execution_time_seconds, "module_output": res1.module_output, "error_log": None})

    res2 = solve(task_fail, "config_002")
    results_list.append({"run_id": "run_002", "status": res2.status, "execution_time_seconds": res2.execution_time_seconds, "module_output": "none", "error_log": res2.error_log})

    # C. Run Packaging Engine
    package_output({"results": results_list})

    # --- D. ASSERTIONS (The Discovery Gating) ---
    print("--- Running Validations ---")
    
    # 1. Verify Logic State
    assert results_list[0]['status'] == "success", "Run 001 should be success"
    assert results_list[1]['status'] == "failed", "Run 002 should be failed"
    
    # 2. Verify File Creation (The Deliverables)
    assert os.path.exists('successful_runs/run_001.json'), "Missing success artifact"
    assert os.path.exists('failed_runs/run_002.json'), "Missing failure artifact"
    assert os.path.exists('saap_skeleton/pipeline.yml'), "Missing pipeline skeleton"

    # 3. Verify Content Integrity
    with open('successful_runs/run_001.json', 'r') as f:
        data = json.load(f)
        assert data['status'] == 'success'
        assert data['module_output'] == 'output_thermal_v1_config_001.zip'

    print("--- All Integrations Passed: Discovery Phase Verified ---")