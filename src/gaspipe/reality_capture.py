#!/usr/bin/env python3
"""
RealityCapture integration for 3D reconstruction.
"""
import csv
import logging
from pathlib import Path

from .subprocess_wrapper import run_subprocess

logger = logging.getLogger(__name__)


class RealityCaptureProcessor:
    """Process images with RealityCapture for camera pose estimation."""
    
    def __init__(self, config: dict):
        self.config = config
        self.rc_path = config.get('rc_path', 'RealityCapture')
        self.rc_settings_path = config.get('rc_settings_path', 'RC_Settings')
    
    def process_images(self, images_dir: Path, output_dir: Path, run_id: str) -> dict:
        """
        Process images with RealityCapture.
        
        Args:
            images_dir: Directory with cubemap images
            output_dir: Directory for RealityCapture output
            run_id: Run UUID for tracing
        
        Returns:
            Dict with output file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        project_file = output_dir / "project.rcproj"
        sparse_ply = output_dir / "sparse_points.ply"
        poses_csv = output_dir / "camera_poses.csv"
        
        # Count input images
        image_files = (list(images_dir.glob("*.png")) + 
                      list(images_dir.glob("*.jpg")))
        
        logger.info(f"Processing {len(image_files)} images with RealityCapture",
                   extra={"run_id": run_id})
        
        # Build RealityCapture command
        rc_settings = Path(self.rc_settings_path)
        
        cmd = [
            self.rc_path,
            '-addFolder', str(images_dir),
            '-align',
            '-selectMaximalComponent',
            '-calculateNormalModel',
        ]
        
        # Add export commands if XML settings exist
        if rc_settings.exists():
            ply_xml = rc_settings / 'ply_export.xml'
            reg_xml = rc_settings / 'reg_export.xml'
            
            if ply_xml.exists():
                cmd.extend(['-exportSparsePointCloud', str(sparse_ply), str(ply_xml)])
            else:
                cmd.extend(['-exportSparsePointCloud', str(sparse_ply)])
            
            if reg_xml.exists():
                cmd.extend(['-exportRegistration', str(poses_csv), str(reg_xml)])
            else:
                cmd.extend(['-exportRegistration', str(poses_csv)])
        else:
            cmd.extend([
                '-exportSparsePointCloud', str(sparse_ply),
                '-exportRegistration', str(poses_csv)
            ])
        
        cmd.extend(['-save', str(project_file), '-quit'])
        
        # Execute RealityCapture
        timeout = self.config.get('processing', {}).get('timeout_minutes', 15) * 60
        
        try:
            run_subprocess(cmd, timeout=timeout, run_id=run_id, 
                         cwd=Path(self.rc_path).parent if Path(self.rc_path).is_file() else None)
            
            # Validate outputs
            if not sparse_ply.exists() or sparse_ply.stat().st_size < 1000:
                raise Exception("RealityCapture did not create valid sparse point cloud")
            
            if not poses_csv.exists() or poses_csv.stat().st_size < 100:
                raise Exception("RealityCapture did not create valid camera poses")
            
            pose_count = self._count_poses(poses_csv)
            
            logger.info(f"RealityCapture complete: {pose_count} camera poses",
                       extra={"run_id": run_id})
            
            return {
                'project_file': project_file,
                'sparse_ply': sparse_ply,
                'poses_csv': poses_csv,
                'pose_count': pose_count
            }
            
        except Exception as e:
            logger.error(f"RealityCapture failed: {e}", extra={"run_id": run_id})
            raise
    
    def _count_poses(self, csv_path: Path) -> int:
        """Count valid poses in CSV - FIXED to skip header."""
        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)  # ✅ Skip header row
                return sum(1 for row in reader 
                          if row and not row[0].startswith('#') and len(row) > 10)
        except:
            return 0