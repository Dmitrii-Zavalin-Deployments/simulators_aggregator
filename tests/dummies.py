
class dummy_in(dict):
    """Maps 1:1 to Tuner Execution Task Schema."""
    def __init__(self, pipeline_id="default_pipeline", config_ids=None, input_data_list=None):
        super().__init__({
            "pipeline_id": pipeline_id,
            "config_ids": config_ids or ["default_config"],
            "input_data_list": input_data_list or ["default_input.json"]
        })
        self.validation_flag = False
        self.is_ready_to_run = True

    def override(self, **kwargs):
        for key, value in kwargs.items():
            if key in self:
                self[key] = value
            else:
                setattr(self, key, value)
        return self

class dummy_out(dict):
    """Maps 1:1 to Tuner Results Schema."""
    def __init__(self, run_id="run_000", status="success", exec_time=0.0, output="output.zip", error=None):
        super().__init__({
            "run_id": run_id,
            "status": status,
            "execution_time_seconds": exec_time,
            "module_output": output,
            "error_log": error
        })
        self.debug_mode = False
        self.log_path = "/tmp/run_log.txt"

    def override(self, **kwargs):
        for key, value in kwargs.items():
            if key in self:
                self[key] = value
            else:
                setattr(self, key, value)
        return self