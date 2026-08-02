#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "DIAGNOSTICS: Inspecting caplog integration in test suite vs logger setup"
echo "=========================================="
echo "--- Updating tests/io/test_state_manager.py to use caplog instead of capsys ---"

sed -i 's/def test_main_missing_env(mock_tm, monkeypatch, capsys):/def test_main_missing_env(mock_tm, monkeypatch, caplog):/g' tests/io/test_state_manager.py
sed -i 's/captured = capsys.readouterr()/l_text = caplog.text/g' tests/io/test_state_manager.py
sed -i 's/assert "CRITICAL ERROR" in captured.err/assert "CRITICAL ERROR" in l_text/g' tests/io/test_state_manager.py

sed -i 's/def test_main_unexpected_exception(mock_tm, monkeypatch, capsys):/def test_main_unexpected_exception(mock_tm, monkeypatch, caplog):/g' tests/io/test_state_manager.py
sed -i 's/captured = capsys.readouterr()/l_text = caplog.text/g' tests/io/test_state_manager.py
sed -i 's/assert "CRITICAL ERROR" in captured.err/assert "CRITICAL ERROR" in l_text/g' tests/io/test_state_manager.py
sed -i 's/assert "Auth Exploded" in captured.err/assert "Auth Exploded" in l_text/g' tests/io/test_state_manager.py

sed -i 's/def test_main_success_found(mock_check, mock_dbx, mock_tm, monkeypatch, capsys):/def test_main_success_found(mock_check, mock_dbx, mock_tm, monkeypatch, caplog):/g' tests/io/test_state_manager.py
sed -i 's/captured = capsys.readouterr()/l_text = caplog.text/g' tests/io/test_state_manager.py
sed -i 's/assert "state_status=found" in captured.out/assert "state_status=found" in l_text/g' tests/io/test_state_manager.py

sed -i 's/def test_main_success_not_found(mock_check, mock_dbx, mock_tm, monkeypatch, capsys):/def test_main_success_not_found(mock_check, mock_dbx, mock_tm, monkeypatch, caplog):/g' tests/io/test_state_manager.py
sed -i 's/captured = capsys.readouterr()/l_text = caplog.text/g' tests/io/test_state_manager.py
sed -i 's/assert "state_status=not_found" in captured.out/assert "state_status=not_found" in l_text/g' tests/io/test_state_manager.py

echo "--- Automated repair complete. Running pytest on test_state_manager.py ---"
# pytest tests/io/test_state_manager.py -v