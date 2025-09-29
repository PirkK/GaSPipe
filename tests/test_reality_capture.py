#!/usr/bin/env python3
"""Unit tests for RealityCaptureProcessor."""
import pytest
from pathlib import Path
from unittest.mock import patch

from gaspipe.reality_capture import RealityCaptureProcessor


@pytest.fixture
def rc_processor(sample_config):
    """Create RealityCaptureProcessor instance."""
    return RealityCaptureProcessor(sample_config)


def test_count_poses(rc_processor, tmp_path):
    """Test camera pose counting from CSV - FIXED."""
    csv_file = tmp_path / "poses.csv"
    csv_file.write_text(
        "img,x,y,z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n"  # Header (skipped)
        "img1.png,0,0,0,1,0,0,0,1,0,0,0,1,50\n"  # Row 1
        "img2.png,1,0,0,1,0,0,0,1,0,0,0,1,50\n"  # Row 2
    )
    
    count = rc_processor._count_poses(csv_file)
    assert count == 2  # ✅ Now correctly counts only data rows


def test_process_images_mock(rc_processor, tmp_path):
    """Test RealityCapture processing with mock."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    output_dir = tmp_path / "rc_output"
    output_dir.mkdir()
    
    # Create fake images
    for i in range(10):
        (images_dir / f"img_{i}.png").write_bytes(b"fake")
    
    # ✅ FIX: Mock run_subprocess in correct module
    with patch('gaspipe.reality_capture.run_subprocess') as mock_run:
        mock_run.return_value = ""
        
        # ✅ FIX: Create fake outputs with MORE CONTENT (> 100 bytes for CSV validation)
        (output_dir / "sparse_points.ply").write_bytes(b"x" * 5000)
        
        # ✅ CRITICAL FIX: CSV must be > 100 bytes AND have multiple data rows
        csv_content = "img,x,y,z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n"  # Header
        for i in range(10):  # Add 10 data rows to ensure > 100 bytes
            csv_content += f"img{i}.png,{i},0,0,1,0,0,0,1,0,0,0,1,50\n"
        
        (output_dir / "camera_poses.csv").write_text(csv_content)
        
        result = rc_processor.process_images(images_dir, output_dir, "test-id")
        
        assert result['pose_count'] == 10  # ✅ Should count 10 data rows
        assert result['sparse_ply'].exists()
        assert result['poses_csv'].exists()
        assert result['poses_csv'].stat().st_size > 100  # ✅ Verify size validation passes
        mock_run.assert_called_once()