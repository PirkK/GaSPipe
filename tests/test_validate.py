#!/usr/bin/env python3
"""Unit tests for validation module."""
import csv
import tempfile
from pathlib import Path

import pytest

from src.gaspipe.validate import (
    validate_frameindex,
    validate_camera_poses,
    validate_checkpoint,
    GaSPipeValidationError
)


def test_validate_frameindex_success():
    """Test successful frame index validation."""
    data = {
        "frame_number": 42,
        "timestamp_sec": 21.0,
        "file_path": Path("/tmp/frame_042.png"),
        "sha256": "a" * 64
    }
    
    frame_idx = validate_frameindex(data)
    assert frame_idx.frame_number == 42
    assert frame_idx.sha256 == "a" * 64


def test_validate_frameindex_negative_number():
    """Test frame index validation with negative frame number."""
    data = {
        "frame_number": -5,
        "timestamp_sec": 0.0,
        "file_path": Path("/tmp/frame.png"),
        "sha256": "a" * 64
    }
    
    with pytest.raises(GaSPipeValidationError) as exc_info:
        validate_frameindex(data)
    
    error_dict = exc_info.value.to_dict()
    assert error_dict["code"] == "INVALID_FRAME_INDEX"
    assert "frame_number" in str(error_dict["details"])


def test_validate_frameindex_invalid_sha256():
    """Test frame index validation with invalid SHA256."""
    data = {
        "frame_number": 0,
        "timestamp_sec": 0.0,
        "file_path": Path("/tmp/frame.png"),
        "sha256": "invalid_checksum"
    }
    
    with pytest.raises(GaSPipeValidationError) as exc_info:
        validate_frameindex(data)
    
    error_dict = exc_info.value.to_dict()
    assert error_dict["code"] == "INVALID_FRAME_INDEX"


def test_validate_camera_poses_success(tmp_path):
    """Test successful camera poses CSV parsing."""
    csv_file = tmp_path / "poses.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['image_name', 'pos_x', 'pos_y', 'pos_z', 
                        'r00', 'r01', 'r02', 'r10', 'r11', 'r12', 'r20', 'r21', 'r22', 'focal'])
        writer.writerow(['img_001.png', '0.0', '0.0', '0.0',
                        '1.0', '0.0', '0.0', '0.0', '1.0', '0.0', '0.0', '0.0', '1.0', '50.0'])
    
    poses = validate_camera_poses(csv_file)
    assert len(poses) == 1
    assert poses[0].image_name == 'img_001.png'
    assert poses[0].focal_length == 50.0


def test_validate_camera_poses_file_not_found():
    """Test camera poses validation with missing file."""
    with pytest.raises(GaSPipeValidationError) as exc_info:
        validate_camera_poses(Path("/nonexistent/poses.csv"))
    
    error_dict = exc_info.value.to_dict()
    assert error_dict["code"] == "POSES_FILE_NOT_FOUND"


def test_validate_camera_poses_empty_csv(tmp_path):
    """Test camera poses validation with empty CSV."""
    csv_file = tmp_path / "empty.csv"
    with open(csv_file, 'w') as f:
        f.write('image_name,pos_x,pos_y,pos_z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n')
    
    with pytest.raises(GaSPipeValidationError) as exc_info:
        validate_camera_poses(csv_file)
    
    error_dict = exc_info.value.to_dict()
    assert error_dict["code"] == "NO_POSES_FOUND"


def test_validate_checkpoint_not_found():
    """Test checkpoint validation with missing file."""
    with pytest.raises(GaSPipeValidationError) as exc_info:
        validate_checkpoint(Path("/nonexistent/checkpoint.json"))
    
    error_dict = exc_info.value.to_dict()
    assert error_dict["code"] == "CHECKPOINT_NOT_FOUND"


def test_validate_checkpoint_success(tmp_path):
    """Test successful checkpoint validation."""
    import json
    from datetime import datetime
    
    checkpoint_file = tmp_path / "checkpoint.json"
    checkpoint_data = {
        "run_id": "12345678-1234-5678-1234-567812345678",
        "video_file": "/tmp/video.mp4",
        "output_dir": "/tmp/output",
        "current_step": "cubemap",
        "manifest": [
            {
                "step": "frames",
                "status": "completed",
                "started_at": datetime.utcnow().isoformat(),
                "outputs": [],
                "sha256_sums": {}
            }
        ],
        "config_snapshot": {},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    
    checkpoint = validate_checkpoint(checkpoint_file)
    assert checkpoint.run_id == "12345678-1234-5678-1234-567812345678"
    assert checkpoint.current_step == "cubemap"