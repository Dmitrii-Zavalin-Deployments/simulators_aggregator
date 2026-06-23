import os
import json
from interfaces.step_interface import StepInterface
from src.state.tuner_state import TunerState

class DeliverableAssemblyStep(StepInterface):
    """
    The Zero-Logic Packager. 
    Constructs the final SaaP deliverables strictly from the Sovereign Container.
    """

    def execute(self, container: TunerState) -> None:
        # 1. Read-Only Schema Extraction
        deliverable_payload = container.to_saap_deliverable()

        # 2. Physical Directory Scaffolding (Refactored from package_output)
        os.makedirs(container.saap_skeleton_path, exist_ok=True)
        
        # 3. Write SaaP Pipeline Skeleton
        pipeline_yml_path = os.path.join(container.saap_skeleton_path, 'pipeline.yml')
        with open(pipeline_yml_path, 'w') as f:
            f.write("# Final ACE Pipeline Config Extracted from Tuner\n")
        
        # 4. Generate Output Manifests (representing the ZIP staging)
        with open(f"{container.success_zip_path}_manifest.json", 'w') as f:
            json.dump(container.successful_runs, f, indent=4)
            
        with open(f"{container.failed_zip_path}_manifest.json", 'w') as f:
            json.dump(container.failed_runs, f, indent=4)
            
        # 5. Write the final Deliverable Schema
        final_schema_path = os.path.join(container.saap_skeleton_path, "deliverable.json")
        with open(final_schema_path, "w") as f:
            json.dump(deliverable_payload, f, indent=4)