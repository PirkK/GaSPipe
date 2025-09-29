#!/usr/bin/env python3
"""Pytest configuration and shared fixtures."""
import pytest
from pathlib import Path


@pytest.fixture
def sample_frame_data():
    """Sample valid frame index data."""
    return {
        "frame_number": 0,
        "timestamp_sec": 0.0,
        "file_path": Path("/tmp/frame_000.png"),
        "sha256": "a" * 64
    }


@pytest.fixture
def sample_config():
    """Sample GaSPipe configuration."""
    return {
        "ffmpeg_path": "ffmpeg",
        "rc_path": "RealityCapture",
        "postshot_path": "postshot-cli",
        "video": {
            "fps": 1.0,
            "resolution": "4K",
            "format": "PNG"
        },
        "cubemap": {
            "size": "1920x1920",
            "format": "PNG"
        },
        "postshot": {
            "profile": "Splat MCMC",
            "steps": 25
        }
    }