# tests/api/test_github_trigger.py

import pytest
import responses
import requests
from unittest.mock import patch
from src.api.github_trigger import Dispatcher
from src.core.constants import OrchestrationStatus

class TestDispatcherForensics:

    def test_init_missing_token(self, monkeypatch):
        """Line 36-39: Verify critical halt if GH_PAT is missing."""
        monkeypatch.delenv("GH_PAT", raising=False)
        with pytest.raises(RuntimeError, match="GH_PAT not found"):
            Dispatcher()

    def test_init_success(self, monkeypatch):
        """Verify headers are correctly seeded when token exists."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        assert dispatcher.token == "mock_token"
        assert dispatcher.headers["Authorization"] == "Bearer mock_token"

    @patch("src.api.github_trigger.time.sleep", return_value=None)
    @responses.activate
    def test_trigger_worker_full_success(self, mock_sleep, monkeypatch):
        """Line 50-97: Verify successful dispatch and traceability link retrieval."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        
        target_repo = "org/worker-repo"
        payload = {"step": "simulation_core", "artifact_id": "v1"}
        
        # Mock 1: The Dispatch POST
        responses.add(
            responses.POST,
            f"https://api.github.com/repos/{target_repo}/dispatches",
            status=204
        )
        
        # Mock 2: The Traceability GET (Workflow Runs)
        run_data = {
            "workflow_runs": [
                {"html_url": "https://github.com/org/worker-repo/actions/runs/12345"}
            ]
        }
        responses.add(
            responses.GET,
            f"https://api.github.com/repos/{target_repo}/actions/runs",
            json=run_data,
            status=200
        )

        result = dispatcher.trigger_worker(target_repo, payload)
        
        assert result is True
        assert payload["status"] == OrchestrationStatus.IN_PROGRESS.value
        # Verify call counts
        assert len(responses.calls) == 2
        mock_sleep.assert_called_once_with(10.0)

    def test_trigger_worker_missing_step_key(self, monkeypatch):
        """Line 68-70: Verify KeyError when payload is malformed."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        
        # Payload missing 'step' key
        bad_payload = {"artifact": "data.zip"}
        
        with pytest.raises(KeyError, match="Step ID missing"):
            dispatcher.trigger_worker("repo", bad_payload)

    @responses.activate
    def test_trigger_worker_handshake_refused(self, monkeypatch):
        """Line 99-100: Verify False return on non-204 response."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        
        responses.add(
            responses.POST,
            "https://api.github.com/repos/repo/dispatches",
            json={"message": "Not Found"},
            status=404
        )
        
        result = dispatcher.trigger_worker("repo", {"step": "init"})
        assert result is False

    @responses.activate
    def test_trigger_worker_connection_error(self, monkeypatch):
        """Line 102-104: Verify resilience against network timeouts/errors."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        
        from requests.exceptions import ConnectTimeout
        responses.add(
            responses.POST,
            "https://api.github.com/repos/repo/dispatches",
            body=ConnectTimeout("Connection timed out")
        )
        
        result = dispatcher.trigger_worker("repo", {"step": "init"})
        assert result is False

    @patch("src.api.github_trigger.time.sleep", return_value=None)
    @responses.activate
    def test_traceability_index_missing(self, mock_sleep, monkeypatch):
        """Line 92-93: Handle case where dispatch is accepted but not yet indexed."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        
        responses.add(responses.POST, "https://api.github.com/repos/repo/dispatches", status=204)
        # Return empty workflow list
        responses.add(responses.GET, "https://api.github.com/repos/repo/actions/runs", json={"workflow_runs": []}, status=200)

        with patch("src.api.github_trigger.logger") as mock_logger:
            result = dispatcher.trigger_worker("repo", {"step": "init"})
            assert result is True
            mock_logger.warning.assert_any_call("🛰️ Signal accepted, but no live run indexed yet for repo.")
        
    @patch("src.api.github_trigger.time.sleep", return_value=None)
    @responses.activate
    def test_traceability_no_runs_indexed(self, mock_sleep, monkeypatch):
        """Covers Line 93: Handshake accepted, but GitHub indexed 0 runs."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        target_repo = "org/repo"
        
        # 1. Success on Dispatch
        responses.add(responses.POST, f"https://api.github.com/repos/{target_repo}/dispatches", status=204)
        
        # 2. Return empty workflow list (Simulating lag in GitHub indexing)
        responses.add(
            responses.GET, 
            f"https://api.github.com/repos/{target_repo}/actions/runs", 
            json={"workflow_runs": []}, 
            status=200
        )

        with patch("src.api.github_trigger.logger") as mock_logger:
            result = dispatcher.trigger_worker(target_repo, {"step": "test-lag"})
            assert result is True  # The dispatch itself worked!
            mock_logger.warning.assert_any_call(f"🛰️ Signal accepted, but no live run indexed yet for {target_repo}.")

    @patch("src.api.github_trigger.time.sleep", return_value=None)
    @responses.activate
    def test_traceability_network_exception(self, mock_sleep, monkeypatch):
        """Covers Lines 94-95: Dispatch success, but Traceability call crashes."""
        monkeypatch.setenv("GH_PAT", "mock_token")
        dispatcher = Dispatcher()
        target_repo = "org/repo"

        # 1. Success on Dispatch
        responses.add(responses.POST, f"https://api.github.com/repos/{target_repo}/dispatches", status=204)
        
        # 2. Simulate a network timeout or DNS failure during the SECOND call
        responses.add(
            responses.GET, 
            f"https://api.github.com/repos/{target_repo}/actions/runs", 
            body=requests.exceptions.ConnectionError("API Offline")
        )

        with patch("src.api.github_trigger.logger") as mock_logger:
            result = dispatcher.trigger_worker(target_repo, {"step": "test-failure"})
            
            # The function should still return True because the dispatch was sent.
            assert result is True 
            # Verify the specific "Traceability Error" warning was logged.
            assert any("Traceability Error" in call.args[0] for call in mock_logger.warning.call_args_list)