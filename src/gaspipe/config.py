#!/usr/bin/env python3
"""Configuration management for GaSPipe."""
import json
from pathlib import Path
from typing import Any


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load configuration from JSON file or return defaults.
    
    Args:
        config_path: Path to config JSON file (optional)
    
    Returns:
        Configuration dictionary
    """
    # Default configuration
    default_config = {
        "ffmpeg_path": "ffmpeg",
        "rc_path": "RealityCapture",
        "postshot_path": "postshot-cli",
        "rc_settings_path": "RC_Settings",
        "video": {
            "fps": 1.0,
            "resolution": "4K",
            "format": "PNG",
            "quality": "high"
        },
        "cubemap": {
            "size": "1920x1920",
            "format": "PNG",
            "quality": "high"
        },
        "postshot": {
            "profile": "Splat MCMC",
            "steps": 25
        },
        "processing": {
            "timeout_minutes": 15
        }
    }
    
    # Load from file if provided
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            
            # Merge with defaults (user config overrides)
            default_config.update(user_config)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid config JSON: {e}")
    
    return default_config


def save_config(config: dict[str, Any], config_path: Path) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save config file
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)