#!/usr/bin/env python3
"""
PostShot integration for Gaussian Splatting training.
"""
import logging
import shutil
from pathlib import Path

from .subprocess_wrapper import run_subprocess

logger = logging.getLogger(__name__)


class PostShotTrainer:
    """Train Gaussian Splats using PostShot CLI."""
    
    def __init__(self, config: dict):
        self.config = config
        self.postshot_path = config.get('postshot_path', 'postshot-cli')
    
    def train(self, images_dir: Path, rc_output: dict, output_dir: Path, 
              video_name: str, run_id: str) -> dict:
        """
        Train Gaussian Splats with PostShot.
        
        Args:
            images_dir: Directory with cubemap images
            rc_output: Dict from RealityCapture with file paths
            output_dir: Directory for PostShot output
            video_name: Name for output project file
            run_id: Run UUID for tracing
        
        Returns:
            Dict with output paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy RealityCapture outputs to images directory
        sparse_ply = Path(rc_output['sparse_ply'])
        poses_csv = Path(rc_output['poses_csv'])
        
        sparse_dest = images_dir / "sparse_points.ply"
        poses_dest = images_dir / "camera_poses.csv"
        
        shutil.copy2(sparse_ply, sparse_dest)
        shutil.copy2(poses_csv, poses_dest)
        
        logger.info(f"Copied RealityCapture outputs to images directory",
                   extra={"run_id": run_id})
        
        # Get PostShot settings
        postshot_config = self.config.get('postshot', {})
        profile = postshot_config.get('profile', 'Splat MCMC')
        steps = postshot_config.get('steps', 25)
        
        # Validate inputs
        image_count = len(list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")))
        pose_count = rc_output.get('pose_count', 0)
        
        logger.info(f"PostShot training: {image_count} images, {pose_count} poses",
                   extra={"run_id": run_id})
        
        if image_count < 10:
            raise Exception(f"Too few images for training: {image_count}")
        
        if pose_count == 0:
            raise Exception("No camera poses available")
        
        # Build PostShot command
        project_file = output_dir / f"{video_name}.psht"
        
        cmd = [
            self.postshot_path,
            'train',
            '--import', str(images_dir),
            '--output', str(project_file),
            '--profile', profile,
            '-s', str(steps),
            '--max-image-size', '0'
        ]
        
        logger.info(f"Starting PostShot: {profile}, {steps}k steps",
                   extra={"run_id": run_id})
        
        # Execute PostShot
        timeout = 3600  # 1 hour
        
        try:
            run_subprocess(cmd, timeout=timeout, run_id=run_id)
            
            if not project_file.exists() or project_file.stat().st_size < 1000:
                raise Exception("PostShot did not create valid project file")
            
            logger.info(f"PostShot training complete: {project_file.name}",
                       extra={"run_id": run_id})
            
            return {
                'project_file': project_file,
                'file_size': project_file.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"PostShot training failed: {e}", extra={"run_id": run_id})
            raise