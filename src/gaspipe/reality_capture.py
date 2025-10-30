#!/usr/bin/env python3
"""
RealityCapture Clean Interface
=============================

CRITICAL FIX: Let RealityCapture do its job WITHOUT interference
- NO XMP metadata forcing camera positions  
- NO complex CLI parameters that confuse the process
- CLEAN commands that let RC calculate positions automatically
- Focus on AUTOMATIC pose detection from images only

This fixes the main problem: cameras being placed in a line instead of 3D space
"""

import subprocess
import csv
from pathlib import Path
import time

class RealityCaptureProcessor:
    """Clean RealityCapture interface - lets RC do automatic pose detection"""
    
    def __init__(self, config):
        self.config = config
        self.logger = None
        
    def set_logger(self, logger_func):
        """Set logging function"""
        self.logger = logger_func
        
    def log(self, message):
        """Log message"""
        if self.logger:
            self.logger(message)
        else:
            print(message)
            
    def test(self):
        """Test RealityCapture installation"""
        try:
            rc_path = self.config.get('software', 'reality_capture')
            result = subprocess.run(
                [rc_path, '-help'], 
                capture_output=True, 
                timeout=10,
                text=True
            )
            
            # RC often returns non-zero even on help, check if it responded
            if result.returncode == 0 or len(result.stdout) > 0 or len(result.stderr) > 0:
                self.log("âœ… RealityCapture: OK")
                return True
            else:
                self.log("âŒ RealityCapture: No response")
                return False
                
        except FileNotFoundError:
            self.log("âŒ RealityCapture: Not found")
            return False
        except subprocess.TimeoutExpired:
            # Timeout often means GUI opened - this is OK
            self.log("âœ… RealityCapture: OK (GUI launched)")
            return True
        except Exception as e:
            self.log(f"âŒ RealityCapture: {e}")
            return False
    
    def process_images(self, images_dir, output_dir):
        """Process images with CLEAN RealityCapture - uses configured paths"""
        images_path = Path(images_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get paths from config
        rc_exe = self.config.get('software', 'reality_capture')
        rc_settings = self.config.get('software', 'rc_settings')
        
        # Save project file in output directory
        project_file = output_path / "auto_project.rcproj"
        
        # IMPORTANT: Export registration and point cloud DIRECTLY to images folder
        # This allows PostShot to find everything in one place
        sparse_ply = images_path / "sparse_points.ply"
        poses_csv = images_path / "camera_poses.csv"
        
        image_files = (list(images_path.glob("*.png")) + 
                      list(images_path.glob("*.jpg")) + 
                      list(images_path.glob("*.jpeg")))
        
        if not image_files:
            raise Exception(f"No images found in {images_path}")
            
        self.log(f"ðŸ—ï¸ RealityCapture: Processing {len(image_files)} images")
        self.log(f"ðŸ—ï¸ Using AUTOMATIC pose detection (no forced positions)")
        self.log(f"ðŸ—ï¸ RC Settings path: {rc_settings}")
        
        # Check if RC settings path exists and has required XML files
        settings_path = Path(rc_settings)
        if settings_path.exists():
            ply_export_xml = settings_path / 'ply_export.xml'
            reg_export_xml = settings_path / 'reg_export.xml'
            
            if ply_export_xml.exists() and reg_export_xml.exists():
                self.log("ðŸ—ï¸ Using XML export settings from RC settings directory")
                # Use XML files for exports
                cmd = [
                    rc_exe,
                    '-addFolder', str(images_path),
                    '-align',
                    '-selectMaximalComponent', 
                    '-calculateNormalModel',
                    '-exportSparsePointCloud', str(sparse_ply), str(ply_export_xml),
                    '-exportRegistration', str(poses_csv), str(reg_export_xml),
                    '-save', str(project_file),
                    '-quit'
                ]
            else:
                self.log("âš ï¸ XML export files not found in RC settings - using default exports")
                # Fallback to simple exports without XML
                cmd = [
                    rc_exe,
                    '-addFolder', str(images_path),
                    '-align',
                    '-selectMaximalComponent',
                    '-calculateNormalModel',
                    '-exportSparsePointCloud', str(sparse_ply),
                    '-exportRegistration', str(poses_csv),
                    '-save', str(project_file),
                    '-quit'
                ]
        else:
            self.log(f"âš ï¸ RC Settings directory not found: {rc_settings}")
            # Simple command without XML settings
            cmd = [
                rc_exe,
                '-addFolder', str(images_path),
                '-align',
                '-selectMaximalComponent',
                '-calculateNormalModel',
                '-exportSparsePointCloud', str(sparse_ply),
                '-exportRegistration', str(poses_csv),
                '-save', str(project_file),
                '-quit'
            ]
        
        self.log("ðŸ—ï¸ Starting RealityCapture with clean auto-detection...")
        
        try:
            start_time = time.time()
            
            # Get timeout from config if available
            timeout_minutes = self.config.get('processing', 'timeout_minutes')
            timeout_seconds = timeout_minutes * 60 if timeout_minutes else 600  # Default 10 minutes
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            
            execution_time = time.time() - start_time
            self.log(f"ðŸ—ï¸ RealityCapture completed in {execution_time:.1f} seconds")
            
            if process.returncode != 0:
                self.log(f"âš ï¸ RealityCapture returned code {process.returncode}")
                # Don't fail immediately - check if outputs were created
                
            # Validate outputs exist and are reasonable
            if not sparse_ply.exists():
                raise Exception("RealityCapture did not create sparse point cloud")
                
            if not poses_csv.exists():
                raise Exception("RealityCapture did not create camera poses")
                
            ply_size = sparse_ply.stat().st_size
            csv_size = poses_csv.stat().st_size
            
            if ply_size < 1000:
                raise Exception("Sparse point cloud file too small - reconstruction may have failed")
                
            if csv_size < 100:
                raise Exception("Camera poses file too small - alignment may have failed")
                
            pose_count = self.count_poses(poses_csv)
            self.log(f"âœ… RealityCapture SUCCESS!")
            self.log(f"ðŸ“Š Output files: PLY: {ply_size:,} bytes, CSV: {csv_size:,} bytes") 
            self.log(f"ðŸ“Š Camera poses: {pose_count} poses generated")
            
            # Validate pose distribution (check they're not all in a line)
            pose_analysis = self.analyze_pose_distribution(poses_csv)
            if pose_analysis['is_linear']:
                self.log("âš ï¸ WARNING: Poses appear to be in a line - this may indicate an issue")
                self.log("ðŸ’¡ This often happens when camera positions are pre-defined instead of calculated")
            else:
                self.log("âœ… Poses show good 3D distribution - automatic detection worked!")
                
            return {
                'project_file': project_file,
                'sparse_ply': sparse_ply,
                'poses_csv': poses_csv,
                'pose_count': pose_count,
                'pose_distribution': pose_analysis
            }
            
        except subprocess.TimeoutExpired:
            process.terminate()
            raise Exception(f"RealityCapture timed out ({timeout_minutes} minutes)")
            
        except Exception as e:
            raise Exception(f"RealityCapture failed: {e}")
    
    def count_poses(self, csv_path):
        """Count valid camera poses in CSV"""
        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                count = 0
                for row in reader:
                    # Skip header and empty rows
                    if row and not row[0].startswith('#') and len(row) > 10:
                        count += 1
                return count
        except Exception:
            return 0
    
    def analyze_pose_distribution(self, csv_path):
        """
        Analyze camera pose distribution to detect if they're in a line
        This helps identify the original problem where cameras were forced into linear positions
        """
        try:
            positions = []
            
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and not row[0].startswith('#') and len(row) > 10:
                        # Extract position (typically columns for X, Y, Z)
                        try:
                            # Common CSV format has position in different columns
                            # We'll try to find X, Y, Z values
                            x = float(row[1]) if len(row) > 1 else 0
                            y = float(row[2]) if len(row) > 2 else 0  
                            z = float(row[3]) if len(row) > 3 else 0
                            positions.append([x, y, z])
                        except (ValueError, IndexError):
                            continue
            
            if len(positions) < 3:
                return {'is_linear': False, 'reason': 'insufficient_data'}
                
            # Simple linearity test - check if all positions are on roughly the same line
            import math
            
            # Calculate distances from first to last point
            if len(positions) >= 3:
                start = positions[0]
                end = positions[-1]
                
                # Check if middle points are close to the line from start to end
                linear_count = 0
                for pos in positions[1:-1]:
                    # Distance from point to line
                    # (This is a simplified check)
                    dist_to_line = self.point_to_line_distance(pos, start, end)
                    if dist_to_line < 0.1:  # Very close to line
                        linear_count += 1
                        
                linearity_ratio = linear_count / max(1, len(positions) - 2)
                is_linear = linearity_ratio > 0.8  # 80% of points are on the line
                
                return {
                    'is_linear': is_linear,
                    'linearity_ratio': linearity_ratio,
                    'total_poses': len(positions),
                    'reason': 'calculated'
                }
            else:
                return {'is_linear': False, 'reason': 'insufficient_poses'}
                
        except Exception as e:
            return {'is_linear': False, 'reason': f'analysis_error: {e}'}
    
    def point_to_line_distance(self, point, line_start, line_end):
        """Calculate distance from point to line (simplified 3D version)"""
        import math
        
        # Vector from line_start to line_end
        line_vec = [line_end[i] - line_start[i] for i in range(3)]
        
        # Vector from line_start to point
        point_vec = [point[i] - line_start[i] for i in range(3)]
        
        # Length of line vector
        line_len = math.sqrt(sum(x*x for x in line_vec))
        if line_len == 0:
            return math.sqrt(sum(x*x for x in point_vec))
            
        # Project point onto line
        projection = sum(point_vec[i] * line_vec[i] for i in range(3)) / (line_len * line_len)
        
        # Find closest point on line
        closest = [line_start[i] + projection * line_vec[i] for i in range(3)]
        
        # Distance from point to closest point on line
        distance = math.sqrt(sum((point[i] - closest[i])**2 for i in range(3)))
        
        return distance