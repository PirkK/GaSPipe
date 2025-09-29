#!/usr/bin/env python3
"""
Robust subprocess wrapper with retry logic and structured error handling.
"""
import logging
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SubprocessError(Exception):
    """Structured subprocess execution error."""
    
    def __init__(self, cmd: list[str], returncode: int, stdout: str, stderr: str, transient: bool):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.transient = transient
        super().__init__(f"Command failed with code {returncode}: {' '.join(cmd)}")

    def to_dict(self) -> dict:
        return {
            "cmd": self.cmd,
            "returncode": self.returncode,
            "stdout": self.stdout[:500],  # Truncate for logging
            "stderr": self.stderr[:500],
            "transient": self.transient
        }


def _is_transient_error(returncode: int, stderr: str) -> bool:
    """Classify error as transient (retryable) or permanent."""
    # Transient indicators
    transient_patterns = [
        "timeout", "timed out",
        "connection", "network",
        "temporarily unavailable",
        "resource busy",
        "lock"
    ]
    
    stderr_lower = stderr.lower()
    if any(pattern in stderr_lower for pattern in transient_patterns):
        return True
    
    # Return codes that suggest transient issues
    transient_codes = {124, 137, 143}  # timeout, SIGKILL, SIGTERM
    if returncode in transient_codes:
        return True
    
    return False


def run_subprocess(
    cmd: list[str],
    timeout: int = 600,
    run_id: Optional[str] = None,
    cwd: Optional[Path] = None,
    retry_max_attempts: int = 5,
    retry_base_delay: float = 2.0,
    retry_max_delay: float = 60.0
) -> str:
    """
    Execute subprocess with retry logic and structured error handling.
    
    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds
        run_id: UUID for tracing (injected into env)
        cwd: Working directory
        retry_max_attempts: Maximum retry attempts for transient errors
        retry_base_delay: Base delay for exponential backoff (seconds)
        retry_max_delay: Maximum retry delay (seconds)
    
    Returns:
        stdout on success
    
    Raises:
        SubprocessError: On permanent failure or max retries exceeded
    """
    env = os.environ.copy()
    if run_id:
        env['GASPIPE_RUN_ID'] = run_id
        logger.info(f"Running subprocess with run_id={run_id}", extra={"run_id": run_id})
    
    attempt = 0
    while attempt < retry_max_attempts:
        attempt += 1
        
        try:
            logger.debug(f"Subprocess attempt {attempt}/{retry_max_attempts}: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=env
            )
            
            if result.returncode == 0:
                logger.info(f"Subprocess succeeded on attempt {attempt}", extra={
                    "cmd": cmd[0],
                    "attempt": attempt,
                    "run_id": run_id
                })
                return result.stdout
            
            # Non-zero exit
            is_transient = _is_transient_error(result.returncode, result.stderr)
            
            if not is_transient or attempt >= retry_max_attempts:
                # Permanent error or max retries reached
                raise SubprocessError(
                    cmd=cmd,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    transient=is_transient
                )
            
            # Retry with exponential backoff + jitter
            delay = min(retry_base_delay * (2 ** (attempt - 1)), retry_max_delay)
            jitter = delay * (0.75 + random.random() * 0.5)  # ±25% jitter
            
            logger.warning(
                f"Transient error on attempt {attempt}, retrying in {jitter:.1f}s",
                extra={
                    "returncode": result.returncode,
                    "stderr_preview": result.stderr[:200],
                    "retry_delay": jitter
                }
            )
            time.sleep(jitter)
            
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Subprocess timeout on attempt {attempt}", extra={"timeout": timeout})
            
            if attempt >= retry_max_attempts:
                raise SubprocessError(
                    cmd=cmd,
                    returncode=124,  # Standard timeout code
                    stdout="",
                    stderr=f"Process timed out after {timeout}s",
                    transient=True
                )
            
            # Retry timeout with backoff
            delay = min(retry_base_delay * (2 ** (attempt - 1)), retry_max_delay)
            jitter = delay * (0.75 + random.random() * 0.5)
            time.sleep(jitter)
    
    # Should not reach here, but safety fallback
    raise SubprocessError(
        cmd=cmd,
        returncode=-1,
        stdout="",
        stderr="Max retries exceeded",
        transient=False
    )