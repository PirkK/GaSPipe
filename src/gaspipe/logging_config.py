#!/usr/bin/env python3
"""
JSON structured logging configuration with run_id tracking.
"""
import json
import logging
import logging.handlers
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with run_id."""
    
    def __init__(self, run_id: Optional[str] = None):
        super().__init__()
        self.run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Add run_id from formatter or record extra
        if self.run_id:
            log_obj["run_id"] = self.run_id
        elif hasattr(record, 'run_id'):
            log_obj["run_id"] = record.run_id
        
        # Add extra fields from record
        if hasattr(record, 'meta'):
            log_obj["meta"] = record.meta
        
        return json.dumps(log_obj)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    run_id: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Configure JSON structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logs (rotates automatically)
        run_id: UUID for run tracking
        max_bytes: Max log file size before rotation
        backup_count: Number of backup files to keep
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    formatter = JSONFormatter(run_id=run_id)
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logging.info(
        "Logging initialized",
        extra={
            "run_id": run_id,
            "meta": {
                "log_level": log_level,
                "log_file": str(log_file) if log_file else None
            }
        }
    )