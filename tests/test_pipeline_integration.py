#!/usr/bin/env python3
"""Integration test for full pipeline with mocks."""
import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from gaspipe.cli import main


@pytest.fixture
def test_environment(tmp_path, monkeypatch):
    """Set up test environment with fixtures and mocks."""
    # Create test directories
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Create minimal test video (placeholder)
    test_video = fixtures_dir / "test_360.mp4"
    test_video.write_bytes(b"FAKE_VIDEO_DATA")
    
    # Point to mock scripts
    mock_scripts_dir = Path(__file__).parent.parent / "scripts"
    monkeypatch.setenv("RC_CLI_PATH", str(mock_scripts_dir / "mock_rc_cli.py"))
    monkeypatch.setenv("POSTSHOT_CLI_PATH", str(mock_scripts_dir / "mock_postshot_cli.py"))
    
    return {
        "video": test_video,
        "output": output_dir,
        "fixtures": fixtures_dir
    }


def test_full_pipeline_run(test_environment, monkeypatch):
    """Test complete pipeline execution with mocks."""
    import sys
    
    # ✅ FIX: Mock ALL subprocess calls before starting pipeline
    with patch('gaspipe.video_processor.run_subprocess') as mock_ffmpeg:
        mock_ffmpeg.return_value = ""
        
        with patch('gaspipe.cubemap_generator.run_subprocess') as mock_cubemap:
            mock_cubemap.return_value = ""
            
            with patch('gaspipe.reality_capture.run_subprocess') as mock_rc:
                mock_rc.return_value = ""
                
                with patch('gaspipe.postshot_trainer.run_subprocess') as mock_ps:
                    mock_ps.return_value = ""
                    
                    # ✅ Mock helper functions
                    with patch('gaspipe.video_processor.is_completed', return_value=False):
                        with patch('gaspipe.video_processor.write_ok_and_sha'):
                            with patch('gaspipe.cubemap_generator.is_completed', return_value=False):
                                with patch('gaspipe.cubemap_generator.write_ok_and_sha'):
                                    
                                    # Create fake outputs for each step
                                    frames_dir = test_environment["output"] / "frames"
                                    frames_dir.mkdir(exist_ok=True)
                                    for i in range(5):
                                        (frames_dir / f"frame_{i:06d}.png").write_bytes(b"fake")
                                    
                                    cubemap_dir = test_environment["output"] / "cubemap_images"
                                    cubemap_dir.mkdir(exist_ok=True)
                                    for i in range(5):
                                        for dir_name in ['front', 'back', 'left', 'right', 'top', 
                                                       'front_right', 'back_right', 'front_left', 'back_left']:
                                            (cubemap_dir / f"frame_{i:06d}_{dir_name}.png").write_bytes(b"fake")
                                    
                                    rc_dir = test_environment["output"] / "realitycapture_output"
                                    rc_dir.mkdir(exist_ok=True)
                                    (rc_dir / "sparse_points.ply").write_bytes(b"x" * 5000)
                                    (rc_dir / "camera_poses.csv").write_text(
                                        "img,x,y,z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n" +
                                        "img,0,0,0,1,0,0,0,1,0,0,0,1,50\n" * 10
                                    )
                                    
                                    splat_dir = test_environment["output"] / "gaussian_splat"
                                    splat_dir.mkdir(exist_ok=True)
                                    (splat_dir / "test_360.psht").write_bytes(b"fake_project" * 1000)
                                    
                                    # Simulate CLI call
                                    test_args = [
                                        'gaspipe',
                                        '--log-level', 'DEBUG',
                                        'run',
                                        str(test_environment["video"]),
                                        str(test_environment["output"])
                                    ]
                                    
                                    monkeypatch.setattr(sys, 'argv', test_args)
                                    
                                    exit_code = main()
                                    
                                    assert exit_code == 0, "Pipeline should complete successfully"
                                    
                                    # Verify checkpoint created
                                    checkpoint_file = test_environment["output"] / "checkpoint.json"
                                    assert checkpoint_file.exists(), "Checkpoint file should exist"
                                    
                                    with open(checkpoint_file) as f:
                                        checkpoint = json.load(f)
                                    
                                    assert "run_id" in checkpoint
                                    assert len(checkpoint["manifest"]) == 4


def test_pipeline_resume(test_environment, monkeypatch):
    """Test pipeline resume from checkpoint."""
    import sys
    
    # Create partial checkpoint with VALID UUID
    checkpoint_file = test_environment["output"] / "checkpoint.json"
    valid_uuid = str(uuid.uuid4())
    
    # Create fake frames directory (step 1 completed)
    frames_dir = test_environment["output"] / "frames"
    frames_dir.mkdir(exist_ok=True)
    for i in range(5):
        (frames_dir / f"frame_{i:06d}.png").write_bytes(b"fake")
    
    checkpoint_data = {
        "run_id": valid_uuid,
        "video_file": str(test_environment["video"]),
        "output_dir": str(test_environment["output"]),
        "current_step": "cubemap",
        "manifest": [
            {
                "step": "frames",
                "status": "completed",
                "started_at": "2025-01-15T10:00:00Z",
                "completed_at": "2025-01-15T10:05:00Z",
                "outputs": [],
                "sha256_sums": {}
            },
            {
                "step": "cubemap",
                "status": "pending",
                "started_at": "2025-01-15T10:05:00Z",
                "outputs": [],
                "sha256_sums": {}
            },
            {
                "step": "realitycapture",
                "status": "pending",
                "started_at": "2025-01-15T10:05:00Z",
                "outputs": [],
                "sha256_sums": {}
            },
            {
                "step": "postshot",
                "status": "pending",
                "started_at": "2025-01-15T10:05:00Z",
                "outputs": [],
                "sha256_sums": {}
            }
        ],
        "config_snapshot": {},
        "created_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:05:00Z"
    }
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    
    # ✅ FIX: Mock subprocess calls for resume
    with patch('gaspipe.cubemap_generator.run_subprocess') as mock_cubemap:
        mock_cubemap.return_value = ""
        
        with patch('gaspipe.reality_capture.run_subprocess') as mock_rc:
            mock_rc.return_value = ""
            
            with patch('gaspipe.postshot_trainer.run_subprocess') as mock_ps:
                mock_ps.return_value = ""
                
                # ✅ Mock helper functions
                with patch('gaspipe.cubemap_generator.is_completed', return_value=False):
                    with patch('gaspipe.cubemap_generator.write_ok_and_sha'):
                        
                        # Create remaining fake outputs
                        cubemap_dir = test_environment["output"] / "cubemap_images"
                        cubemap_dir.mkdir(exist_ok=True)
                        for i in range(5):
                            for dir_name in ['front', 'back', 'left', 'right', 'top',
                                           'front_right', 'back_right', 'front_left', 'back_left']:
                                (cubemap_dir / f"frame_{i:06d}_{dir_name}.png").write_bytes(b"fake")
                        
                        rc_dir = test_environment["output"] / "realitycapture_output"
                        rc_dir.mkdir(exist_ok=True)
                        (rc_dir / "sparse_points.ply").write_bytes(b"x" * 5000)
                        
                        # ✅ CRITICAL FIX: Create CSV with MORE content (> 100 bytes AND valid data rows)
                        csv_content = "img,x,y,z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n"  # Header
                        for i in range(20):  # ✅ 20 rows to ensure > 100 bytes AND valid pose count
                            csv_content += f"img{i}.png,{i},0,0,1,0,0,0,1,0,0,0,1,50\n"
                        
                        (rc_dir / "camera_poses.csv").write_text(csv_content)
                        
                        splat_dir = test_environment["output"] / "gaussian_splat"
                        splat_dir.mkdir(exist_ok=True)
                        (splat_dir / "test_360.psht").write_bytes(b"fake_project" * 1000)
                        
                        # Resume pipeline
                        test_args = [
                            'gaspipe',
                            'resume',
                            str(test_environment["output"])
                        ]
                        
                        monkeypatch.setattr(sys, 'argv', test_args)
                        
                        exit_code = main()
                        
                        assert exit_code == 0, "Resume should complete successfully"
                        
                        # Verify checkpoint updated
                        with open(checkpoint_file) as f:
                            updated_checkpoint = json.load(f)
                        
                        # Verify it's the same run_id
                        assert updated_checkpoint["run_id"] == valid_uuid
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    
    # ✅ FIX: Mock subprocess calls for resume
    with patch('gaspipe.cubemap_generator.run_subprocess') as mock_cubemap:
        mock_cubemap.return_value = ""
        
        with patch('gaspipe.reality_capture.run_subprocess') as mock_rc:
            mock_rc.return_value = ""
            
            with patch('gaspipe.postshot_trainer.run_subprocess') as mock_ps:
                mock_ps.return_value = ""
                
                # ✅ Mock helper functions
                with patch('gaspipe.cubemap_generator.is_completed', return_value=False):
                    with patch('gaspipe.cubemap_generator.write_ok_and_sha'):
                        
                        # Create remaining fake outputs
                        cubemap_dir = test_environment["output"] / "cubemap_images"
                        cubemap_dir.mkdir(exist_ok=True)
                        for i in range(5):
                            for dir_name in ['front', 'back', 'left', 'right', 'top',
                                           'front_right', 'back_right', 'front_left', 'back_left']:
                                (cubemap_dir / f"frame_{i:06d}_{dir_name}.png").write_bytes(b"fake")
                        
                        rc_dir = test_environment["output"] / "realitycapture_output"
                        rc_dir.mkdir(exist_ok=True)
                        (rc_dir / "sparse_points.ply").write_bytes(b"x" * 5000)
                        (rc_dir / "camera_poses.csv").write_text(
                            "img,x,y,z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal\n" +
                            "img,0,0,0,1,0,0,0,1,0,0,0,1,50\n" * 10
                        )
                        
                        splat_dir = test_environment["output"] / "gaussian_splat"
                        splat_dir.mkdir(exist_ok=True)
                        (splat_dir / "test_360.psht").write_bytes(b"fake_project" * 1000)
                        
                        # Resume pipeline
                        test_args = [
                            'gaspipe',
                            'resume',
                            str(test_environment["output"])
                        ]
                        
                        monkeypatch.setattr(sys, 'argv', test_args)
                        
                        exit_code = main()
                        
                        assert exit_code == 0, "Resume should complete successfully"
                        
                        # Verify checkpoint updated
                        with open(checkpoint_file) as f:
                            updated_checkpoint = json.load(f)
                        
                        # Verify it's the same run_id
                        assert updated_checkpoint["run_id"] == valid_uuid


def test_pipeline_all_steps_mock(test_environment, monkeypatch):
    """Test complete pipeline with all steps mocked."""
    import sys
    
    # Setup mocks for all subprocess calls
    with patch('gaspipe.subprocess_wrapper.run_subprocess') as mock_run:
        mock_run.return_value = ""
        
        # Mock file creation for each step
        with patch('gaspipe.video_processor.VideoProcessor.extract_frames') as mock_frames:
            mock_frames.return_value = 10  # 10 frames
            
            with patch('gaspipe.cubemap_generator.CubemapGenerator.generate_cubemap') as mock_cubemap:
                mock_cubemap.return_value = 90  # 10 frames * 9 directions
                
                with patch('gaspipe.reality_capture.RealityCaptureProcessor.process_images') as mock_rc:
                    # Create fake output files in test environment
                    rc_output_dir = test_environment["output"] / "realitycapture_output"
                    rc_output_dir.mkdir(exist_ok=True)
                    
                    fake_ply = rc_output_dir / "sparse_points.ply"
                    fake_csv = rc_output_dir / "camera_poses.csv"
                    fake_ply.write_bytes(b"fake_ply_data" * 100)
                    fake_csv.write_text("fake,csv,data\n" * 10)
                    
                    mock_rc.return_value = {
                        'sparse_ply': fake_ply,
                        'poses_csv': fake_csv,
                        'pose_count': 90
                    }
                    
                    with patch('gaspipe.postshot_trainer.PostShotTrainer.train') as mock_ps:
                        # Create fake PostShot output
                        splat_dir = test_environment["output"] / "gaussian_splat"
                        splat_dir.mkdir(exist_ok=True)
                        fake_project = splat_dir / "test_360.psht"
                        fake_project.write_bytes(b"fake_project_data" * 1000)
                        
                        mock_ps.return_value = {
                            'project_file': fake_project,
                            'file_size': 50000
                        }
                        
                        # Run pipeline
                        test_args = [
                            'gaspipe',
                            '--log-level', 'DEBUG',
                            'run',
                            str(test_environment["video"]),
                            str(test_environment["output"])
                        ]
                        
                        monkeypatch.setattr(sys, 'argv', test_args)
                        exit_code = main()
                        
                        assert exit_code == 0, "Pipeline should complete successfully"
                        
                        # Verify all steps were called
                        mock_frames.assert_called_once()
                        mock_cubemap.assert_called_once()
                        mock_rc.assert_called_once()
                        mock_ps.assert_called_once()
                        
                        # Verify checkpoint shows completion
                        checkpoint_file = test_environment["output"] / "checkpoint.json"
                        with open(checkpoint_file) as f:
                            checkpoint = json.load(f)
                        
                        # Should have progressed through all steps
                        completed_steps = [
                            entry["step"] for entry in checkpoint["manifest"]
                            if entry["status"] == "completed"
                        ]
                        assert len(completed_steps) >= 1, "At least one step should be completed"