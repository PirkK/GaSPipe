#!/usr/bin/env python3
"""
Clean PostShot Trainer
======================

Simple, working interface to PostShot CLI
- Uses correct CLI syntax that actually works
- Handles file preparation properly  
- Clean error handling and validation
"""

import subprocess
import shutil
from pathlib import Path
import time

class PostShotTrainer:
    """Clean PostShot interface - uses working CLI syntax"""
    
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
        """Test PostShot installation"""
        try:
            postshot_path = self.config.get('software', 'postshot')
            result = subprocess.run(
                [postshot_path, '--help'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            # PostShot returns help in stderr typically
            if result.returncode == 0 or 'usage' in result.stderr.lower() or 'postshot' in result.stderr.lower():
                self.log("âœ… PostShot: OK")
                return True
            else:
                self.log("âŒ PostShot: No valid response")
                return False
                
        except FileNotFoundError:
            self.log("âŒ PostShot: Not found")
            return False
        except Exception as e:
            self.log(f"âŒ PostShot: {e}")
            return False
    
    def train(self, images_dir, reality_capture_output, output_dir):
        """Train Gaussian Splats using PostShot with COMPLETE parameter support"""
        images_path = Path(images_dir)
        rc_output = reality_capture_output
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Validate inputs
        if not images_path.exists():
            raise Exception(f"Images directory not found: {images_path}")
            
        sparse_ply = Path(rc_output['sparse_ply'])
        poses_csv = Path(rc_output['poses_csv'])
        
        if not sparse_ply.exists():
            raise Exception(f"Sparse point cloud not found: {sparse_ply}")
            
        if not poses_csv.exists():
            raise Exception(f"Camera poses not found: {poses_csv}")
        
        # Check image count
        image_files = (list(images_path.glob("*.png")) + 
                      list(images_path.glob("*.jpg")) + 
                      list(images_path.glob("*.jpeg")))
        
        if len(image_files) < 10:
            raise Exception(f"Too few images for training: {len(image_files)}")
            
        # Prepare PostShot input - copy required files to images directory
        sparse_dest = images_path / "sparse_points.ply" 
        poses_dest = images_path / "camera_poses.csv"
        
        self.log(f"ðŸŽ¯ Preparing PostShot input: {len(image_files)} images")
        
        # Copy files if needed or if different
        if not sparse_dest.exists() or sparse_dest.stat().st_size != sparse_ply.stat().st_size:
            shutil.copy2(sparse_ply, sparse_dest)
            self.log(f"ðŸ“‹ Copied sparse points: {sparse_ply.stat().st_size:,} bytes")
            
        if not poses_dest.exists() or poses_dest.stat().st_size != poses_csv.stat().st_size:
            shutil.copy2(poses_csv, poses_dest)
            self.log(f"ðŸ“‹ Copied camera poses: {poses_csv.stat().st_size:,} bytes")
        
        # Validate pose count vs image count
        pose_count = self._count_poses(poses_dest)
        self.log(f"ðŸ“Š PostShot validation: {len(image_files)} images, {pose_count} poses")
        
        if pose_count == 0:
            raise Exception("No valid camera poses found")
            
        # Warn if pose recovery is very low
        pose_ratio = pose_count / len(image_files) if len(image_files) > 0 else 0
        if pose_ratio < 0.3:  # Less than 30% pose recovery
            self.log(f"âš ï¸ Warning: Low pose recovery rate ({pose_count}/{len(image_files)} = {pose_ratio:.1%})")
        elif pose_ratio > 2.0:  # More than 2x poses (could indicate multiple poses per image)
            self.log(f"â„¹ï¸ High pose count - likely multiple views per frame ({pose_count}/{len(image_files)} = {pose_ratio:.1%})")
        
        # Get ALL training settings from config
        profile = self.config.get('postshot', 'profile')
        trainsteps = self.config.get('postshot', 'trainsteps')
        postshot_exe = self.config.get('software', 'postshot')
        
        # Create output project file
        project_name = images_path.parent.name or "gaussian_splat"
        project_file = output_path / f"{project_name}.psht"
        
        # Build PostShot command using CORRECT working syntax
        cmd = [
            postshot_exe,
            'train',                        # Subcommand (required)
            '--import', str(images_path),   # Import from directory (correct parameter)
            '--output', str(project_file),  # Output project file
            '--profile', profile,           # Training profile from config
            '-s', str(trainsteps),         # Training steps in thousands (correct short form)
            '--max-image-size', '0'        # No image resizing (preserves quality)
        ]
        
        self.log(f"ðŸŽ¯ PostShot training configuration:")
        self.log(f"   â€¢ Profile: {profile}")
        self.log(f"   â€¢ Training steps: {trainsteps}k ({trainsteps * 1000} total steps)")
        self.log(f"   â€¢ Executable: {Path(postshot_exe).name}")
        self.log(f"ðŸŽ¯ Starting training...")
        
        # Execute PostShot with progress monitoring
        try:
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor training progress with more frequent updates for long training
            last_log_time = 0
            log_interval = 30 if trainsteps <= 10 else 60  # More frequent for shorter training
            
            while process.poll() is None:
                time.sleep(5)  # Check every 5 seconds
                
                current_time = time.time()
                if current_time - last_log_time > log_interval:
                    last_log_time = current_time
                    elapsed_min = (current_time - start_time) / 60
                    
                    # Estimate progress (very rough)
                    if trainsteps <= 10:
                        estimated_total_min = trainsteps * 2  # ~2 min per 1k steps for small datasets
                    elif trainsteps <= 25:
                        estimated_total_min = trainsteps * 3  # ~3 min per 1k steps for medium datasets  
                    else:
                        estimated_total_min = trainsteps * 4  # ~4 min per 1k steps for large datasets
                        
                    progress_pct = min(95, (elapsed_min / estimated_total_min) * 100) if estimated_total_min > 0 else 0
                    
                    self.log(f"ðŸŽ¯ Training progress: {elapsed_min:.1f}min elapsed (~{progress_pct:.0f}% estimated)")
            
            stdout, stderr = process.communicate()
            execution_time = time.time() - start_time
            
            # Check result
            if process.returncode != 0:
                self.log(f"âŒ PostShot failed with return code {process.returncode}")
                if stderr:
                    self.log(f"âŒ Error output: {stderr[:500]}...")
                if stdout:
                    self.log(f"ðŸ“ Standard output: {stdout[:300]}...")
                raise Exception("PostShot training failed - check error output above")
            
            # Validate output file was created
            if not project_file.exists():
                raise Exception("PostShot did not create project file")
                
            file_size = project_file.stat().st_size
            if file_size < 1000:  # Less than 1KB indicates failure
                raise Exception("PostShot project file too small (training may have failed)")
            
            # Success!
            execution_min = execution_time / 60
            self.log(f"âœ… PostShot training completed successfully!")
            self.log(f"â±ï¸ Training time: {execution_min:.1f} minutes")
            self.log(f"ðŸ“Š Output: {project_file.name} ({file_size:,} bytes)")
            
            # Look for additional output files (splat files, etc.)
            additional_files = []
            for ext in ['.ply', '.splat', '.txt']:
                additional_files.extend(list(output_path.glob(f"*{ext}")))
                
            if additional_files:
                self.log(f"ðŸ“Š Additional outputs: {len(additional_files)} files")
                for add_file in additional_files[:3]:  # Show first 3
                    self.log(f"   â€¢ {add_file.name} ({add_file.stat().st_size:,} bytes)")
            
            return {
                'project_file': project_file,
                'file_size': file_size,
                'training_time': execution_time,
                'additional_files': additional_files,
                'training_steps': trainsteps * 1000,
                'profile_used': profile
            }
            
        except subprocess.TimeoutExpired:
            process.terminate()
            timeout_min = (time.time() - start_time) / 60
            raise Exception(f"PostShot training timed out after {timeout_min:.1f} minutes")
        except Exception as e:
            elapsed_min = (time.time() - start_time) / 60 if 'start_time' in locals() else 0
            raise Exception(f"PostShot training failed after {elapsed_min:.1f}min: {e}")
    
    def _count_poses(self, csv_path):
        """Count valid poses in CSV file"""
        try:
            import csv
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                count = 0
                for row in reader:
                    # Skip header, comments, and empty rows
                    if row and not row[0].startswith('#') and len(row) > 5:
                        count += 1
                return count
        except Exception:
            return 0
    
    def validate_inputs(self, images_dir, reality_capture_output):
        """Validate that inputs are suitable for PostShot training"""
        issues = []
        
        # Check images directory
        images_path = Path(images_dir)
        if not images_path.exists():
            issues.append("Images directory does not exist")
            return issues
            
        image_files = (list(images_path.glob("*.png")) + 
                      list(images_path.glob("*.jpg")) + 
                      list(images_path.glob("*.jpeg")))
        
        if len(image_files) < 10:
            issues.append(f"Too few images: {len(image_files)} (need at least 10)")
        elif len(image_files) < 50:
            issues.append(f"Low image count: {len(image_files)} (recommended: 50+)")
            
        # Check RealityCapture outputs
        if 'sparse_ply' not in reality_capture_output:
            issues.append("Missing sparse point cloud from RealityCapture")
        else:
            ply_path = Path(reality_capture_output['sparse_ply'])
            if not ply_path.exists():
                issues.append("Sparse point cloud file not found")
            elif ply_path.stat().st_size < 1000:
                issues.append("Sparse point cloud file too small")
                
        if 'poses_csv' not in reality_capture_output:
            issues.append("Missing camera poses from RealityCapture")
        else:
            csv_path = Path(reality_capture_output['poses_csv'])
            if not csv_path.exists():
                issues.append("Camera poses file not found")
            else:
                pose_count = self._count_poses(csv_path)
                if pose_count == 0:
                    issues.append("No valid camera poses found")
                elif pose_count < len(image_files) * 0.3:
                    issues.append(f"Very low pose recovery: {pose_count}/{len(image_files)}")
                    
        return issues
    
    def get_training_estimate(self, images_dir):
        """Estimate training time and requirements"""
        try:
            images_path = Path(images_dir)
            image_files = (list(images_path.glob("*.png")) + 
                          list(images_path.glob("*.jpg")) + 
                          list(images_path.glob("*.jpeg")))
            
            image_count = len(image_files)
            steps = self.config.get('postshot', 'steps')
            
            # Rough estimates based on typical performance
            # These are very approximate and depend on hardware
            if image_count < 100:
                time_estimate_min = steps * 0.5  # 0.5 min per 1k steps
            elif image_count < 300:
                time_estimate_min = steps * 1.0  # 1 min per 1k steps  
            else:
                time_estimate_min = steps * 2.0  # 2 min per 1k steps
                
            # Estimate storage requirements
            # PostShot projects can be quite large
            estimated_storage_mb = image_count * 2  # Rough estimate: 2MB per image
            
            return {
                'image_count': image_count,
                'training_steps': steps * 1000,  # Convert to actual steps
                'estimated_time_min': int(time_estimate_min),
                'estimated_storage_mb': estimated_storage_mb
            }
            
        except Exception:
            return None