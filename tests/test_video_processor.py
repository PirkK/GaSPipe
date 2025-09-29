#!/usr/bin/env python3
"""Unit tests for VideoProcessor."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gaspipe.video_processor import VideoProcessor


@pytest.fixture
def video_processor(sample_config):
    """Create VideoProcessor instance with sample config."""
    return VideoProcessor(sample_config)


def test_parse_resolution_4k(video_processor):
    """Test resolution parsing for 4K."""
    width, height = video_processor._parse_resolution("4K")
    assert width == 3840
    assert height == 1920


def test_parse_resolution_8k(video_processor):
    """Test resolution parsing for 8K."""
    width, height = video_processor._parse_resolution("8K")
    assert width == 7680
    assert height == 3840


def test_get_quality_value(video_processor):
    """Test quality parameter conversion."""
    assert video_processor._get_quality_value("high") == "2"
    assert video_processor._get_quality_value("medium") == "5"
    assert video_processor._get_quality_value("low") == "8"


def test_validate_video_success(video_processor, tmp_path):
    """Test video validation with valid file."""
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake_video_data" * 1000000)  # > 1MB
    
    is_valid, message = video_processor.validate_video(video_file)
    assert is_valid
    assert "Valid" in message


def test_validate_video_not_exists(video_processor):
    """Test video validation with non-existent file."""
    is_valid, message = video_processor.validate_video(Path("/nonexistent.mp4"))
    assert not is_valid
    assert "does not exist" in message


def test_validate_video_wrong_extension(video_processor, tmp_path):
    """Test video validation with unsupported format."""
    video_file = tmp_path / "test.txt"
    video_file.write_bytes(b"x" * 2000000)
    
    is_valid, message = video_processor.validate_video(video_file)
    assert not is_valid
    assert "Unsupported format" in message


def test_extract_frames_mock(video_processor, tmp_path):
    """Test frame extraction with mocked subprocess."""
    video_file = tmp_path / "input.mp4"
    video_file.write_bytes(b"fake_video")
    output_dir = tmp_path / "frames"
    output_dir.mkdir()
    
    # ✅ FIX: Mock run_subprocess in correct module
    with patch('gaspipe.video_processor.run_subprocess') as mock_run:
        mock_run.return_value = ""  # Success
        
        # Create fake output frames BEFORE calling extract_frames
        for i in range(5):
            frame_file = output_dir / f"frame_{i:06d}.png"
            frame_file.write_bytes(b"fake_frame")
        
        # ✅ FIX: Mock is_completed to avoid .ok/.sha256 checks
        with patch('gaspipe.video_processor.is_completed', return_value=False):
            with patch('gaspipe.video_processor.write_ok_and_sha'):
                frame_count = video_processor.extract_frames(video_file, output_dir, "test-run-id")
                
                assert frame_count == 5
                mock_run.assert_called_once()
                
                # Verify FFmpeg command structure
                cmd = mock_run.call_args[0][0]
                assert cmd[0] == 'ffmpeg'
                assert '-i' in cmd
                assert str(video_file) in cmd