#!/usr/bin/env python3
"""Unit tests for CubemapGenerator."""
import pytest
from pathlib import Path
from unittest.mock import patch

from gaspipe.cubemap_generator import CubemapGenerator


@pytest.fixture
def cubemap_generator(sample_config):
    """Create CubemapGenerator instance."""
    return CubemapGenerator(sample_config)


def test_parse_cubemap_size(cubemap_generator):
    """Test cubemap size parsing."""
    assert cubemap_generator._parse_cubemap_size("1920x1920") == 1920
    assert cubemap_generator._parse_cubemap_size("960x960") == 960


def test_get_quality_value(cubemap_generator):
    """Test quality parameter conversion."""
    assert cubemap_generator._get_quality_value("high") == "1"
    assert cubemap_generator._get_quality_value("medium") == "4"


def test_directions_count(cubemap_generator):
    """Test that 9 directions are defined."""
    assert len(cubemap_generator.DIRECTIONS) == 9
    
    # Verify direction names
    dir_names = [name for name, _, _ in cubemap_generator.DIRECTIONS]
    assert 'front' in dir_names
    assert 'top' in dir_names


def test_generate_cubemap_mock(cubemap_generator, tmp_path):
    """Test cubemap generation with mocked subprocess."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    output_dir = tmp_path / "cubemap"
    output_dir.mkdir()
    
    # Create fake frame files
    for i in range(3):
        (frames_dir / f"frame_{i:06d}.png").write_bytes(b"fake_frame")
    
    # ✅ FIX: Mock run_subprocess in correct module
    with patch('gaspipe.cubemap_generator.run_subprocess') as mock_run:
        mock_run.return_value = ""
        
        # ✅ FIX: Mock is_completed to return False
        with patch('gaspipe.cubemap_generator.is_completed', return_value=False):
            # ✅ FIX: Mock write_ok_and_sha to avoid file operations
            with patch('gaspipe.cubemap_generator.write_ok_and_sha'):
                count = cubemap_generator.generate_cubemap(frames_dir, output_dir, "test-id")
                
                # 3 frames * 9 directions = 27 calls
                assert mock_run.call_count == 27
                assert count == 27