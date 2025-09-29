#!/usr/bin/env python3
"""Unit tests for PostShotTrainer."""
import pytest
from pathlib import Path
from unittest.mock import patch

from gaspipe.postshot_trainer import PostShotTrainer


@pytest.fixture
def postshot_trainer(sample_config):
    """Create PostShotTrainer instance."""
    return PostShotTrainer(sample_config)


def test_train_mock(postshot_trainer, tmp_path):
    """Test PostShot training with mock."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    rc_output_dir = tmp_path / "rc_output"
    rc_output_dir.mkdir()
    output_dir = tmp_path / "splat"
    output_dir.mkdir()
    
    # Create fake inputs
    for i in range(20):
        (images_dir / f"img_{i}.png").write_bytes(b"fake")
    
    sparse_ply = rc_output_dir / "sparse_points.ply"
    poses_csv = rc_output_dir / "camera_poses.csv"
    sparse_ply.write_bytes(b"x" * 5000)
    poses_csv.write_text(
        "img,x,y,z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n" +  # Header
        "img,0,0,0,1,0,0,0,1,0,0,0,1,50\n" * 10  # 10 data rows
    )
    
    rc_output = {
        'sparse_ply': sparse_ply,
        'poses_csv': poses_csv,
        'pose_count': 10
    }
    
    # ✅ FIX: Mock run_subprocess in correct module
    with patch('gaspipe.postshot_trainer.run_subprocess') as mock_run:
        mock_run.return_value = ""
        
        # Create fake output BEFORE calling train
        project_file = output_dir / "test_video.psht"
        project_file.write_bytes(b"fake_project" * 1000)
        
        result = postshot_trainer.train(images_dir, rc_output, output_dir, "test_video", "test-id")
        
        assert result['project_file'] == project_file
        assert result['file_size'] > 1000
        mock_run.assert_called_once()
        
        # Verify PostShot command structure
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == 'postshot-cli'
        assert 'train' in cmd
        assert '--import' in cmd