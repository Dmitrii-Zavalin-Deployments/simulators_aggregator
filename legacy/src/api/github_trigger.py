# src/api/github_trigger.py

import os
import logging
import requests
import time
from typing import Dict, Any

# Internal Core Imports
from src.core.constants import OrchestrationStatus

# Configure Logger for Dispatch Traceability
logger = logging.getLogger("Engine.Dispatcher")

class Dispatcher:
    """
    The Command Link (Dispatch Protocol).
    Compliance: 
    - Rule 0: __slots__ Mandatory Architecture
    - Rule 3: Remote Dispatch Logic
    - Rule 4: Zero-Default Policy
    - Rule 5: Traceability Loop (Phase C - 10s Reliability)
    """
    
    # Rule 0: Mandatory __slots__ to eliminate dict overhead
    __slots__ = ['token', 'headers']

    def __init__(self):
        """
        Initializes the Dispatcher with explicit environment validation.
        Rule 4: Explicit or Error - No hardcoded fallback tokens.
        """
        # Phase C: Rule 4 - Zero-Default Policy (Explicit or Error)
        self.token = os.getenv("GH_PAT")
        
        if not self.token:
            logger.critical("GH_PAT not found in environment. Access Denied.")
            raise RuntimeError("❌ CRITICAL: GH_PAT not found. Dispatch aborted.")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def trigger_worker(self, target_repo: str, payload: Dict[str, Any]) -> bool:
        """
        Sends a Repository Dispatch signal and retrieves the Live Action Link.
        Rule 1: Isolation Mandate - Targets specific worker repos.
        """
        url = f"https://api.github.com/repos/{target_repo}/dispatches"
        
        # --- LOGICAL WIRING ---
        # We ensure the payload includes the centralized IN_PROGRESS status.
        if "status" not in payload:
            payload["status"] = OrchestrationStatus.IN_PROGRESS.value

        # PHASE C ALIGNMENT: Identifying the Triggerer
        data = {
            "event_type": "artifact_driven_simulation_engine",
            "client_payload": payload
        }

        try:
            # Rule 4: Explicit access for logging
            step_name = payload['step'] 
            logger.info(f"📡 Dispatching Signal: [{target_repo}] for Step [{step_name}]")
        except KeyError:
            logger.critical("Dispatch Payload missing 'step' key. Protocol Breach.")
            raise KeyError("❌ CRITICAL: Step ID missing from dispatch payload.")

        try:
            # Phase 1: Fire the Dispatch Command (15s network timeout)
            response = requests.post(url, json=data, headers=self.headers, timeout=15)
            
            if response.status_code == 204:
                logger.info(f"🚀 Signal Accepted: {target_repo} Handshake Confirmed.")
                
                # --- TRACEABILITY LOOP (10s RELIABILITY) ---
                # We wait 10 seconds to ensure the GitHub API has registered the run.
                # Total cycle time for a batch of 20 jobs: ~3.5 minutes.
                time.sleep(10.0)
                
                runs_url = f"https://api.github.com/repos/{target_repo}/actions/runs?event=repository_dispatch"
                try:
                    run_info = requests.get(runs_url, headers=self.headers, timeout=10).json()
                    if run_info.get('workflow_runs'):
                        # The first item in the list is the most recent dispatch run
                        latest_run = run_info['workflow_runs'][0]['html_url']
                        # Traceability: Including the repo name in the link message
                        logger.info(f"🔗 Live Workflow Link [{target_repo}]: {latest_run}")
                    else:
                        logger.warning(f"🛰️ Signal accepted, but no live run indexed yet for {target_repo}.")
                except Exception as e:
                    logger.warning(f"⚠️ Traceability Error: Could not fetch link for {target_repo}. {e}")
                
                return True
            
            logger.error(f"❌ Handshake Refused: HTTP {response.status_code} - {response.text}")
            return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Connection Error during Dispatch to {target_repo}: {e}")
            return False