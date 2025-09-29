#!/usr/bin/env python3
"""Unit tests for subprocess wrapper."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.gaspipe.subprocess_wrapper import run_subprocess, SubprocessError, _is_transient_error


def test_successful_execution():
    """Test successful subprocess execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success output",
            stderr=""
        )
        
        result = run_subprocess(['echo', 'test'], run_id='test-123')
        
        assert result == "success output"
        mock_run.assert_called_once()
        
        # Verify run_id injected into env
        call_env = mock_run.call_args[1]['env']
        assert call_env['GASPIPE_RUN_ID'] == 'test-123'


def test_retry_on_transient_error():
    """Test retry logic for transient errors."""
    with patch('subprocess.run') as mock_run, patch('time.sleep'):
        # First call fails with transient error, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=124, stdout="", stderr="timeout error"),
            MagicMock(returncode=0, stdout="success", stderr="")
        ]
        
        result = run_subprocess(['test'], retry_max_attempts=3, retry_base_delay=0.1)
        
        assert result == "success"
        assert mock_run.call_count == 2


def test_fail_on_permanent_error():
    """Test immediate failure on permanent errors."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="file not found"
        )
        
        with pytest.raises(SubprocessError) as exc_info:
            run_subprocess(['test'], retry_max_attempts=3)
        
        assert exc_info.value.returncode == 1
        assert not exc_info.value.transient
        mock_run.assert_called_once()  # No retry for permanent errors


def test_max_retries_exceeded():
    """Test failure after max retries exceeded."""
    with patch('subprocess.run') as mock_run, patch('time.sleep'):
        mock_run.return_value = MagicMock(
            returncode=124,
            stdout="",
            stderr="timeout"
        )
        
        with pytest.raises(SubprocessError) as exc_info:
            run_subprocess(['test'], retry_max_attempts=3, retry_base_delay=0.1)
        
        assert mock_run.call_count == 3
        assert exc_info.value.transient


def test_is_transient_error_timeout():
    """Test transient error classification for timeouts."""
    assert _is_transient_error(124, "command timed out")
    assert _is_transient_error(137, "killed")


def test_is_transient_error_permanent():
    """Test permanent error classification."""
    assert not _is_transient_error(1, "file not found")
    assert not _is_transient_error(127, "command not found")