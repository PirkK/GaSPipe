#!/usr/bin/env python3
"""
Cubemap generation from equirectangular frames.
"""
import logging
from pathlib import Path

from .subprocess_wrapper import run_subprocess
from .io_helpers import write_ok_and_sha, is_completed

logger = logging.getLogger(__name__)


class CubemapGenerator:
    """Generate cubemap images from equirectangular frames."""
    
    # 9 directions for comprehensive coverage
    DIRECTIONS = [
        ('front', 0, 0),
        ('right', 90, 0),
        ('back', 180, 0),
        ('left', -90, 0),
        ('front_right', 45, 0),
        ('back_right', 135, 0),
        ('back_left', -135, 0),
        ('front_left', -45, 0),
        ('top', 0, 90)
    ]
    
    def __init__(self, config: dict):
        self.config = config
        self.ffmpeg_path = config.get('ffmpeg_path', 'ffmpeg')
    
    def generate_cubemap(self, frames_dir: Path, output_dir: Path, run_id: str) -> int:
        """
        Generate cubemap images from frames.
        
        Args:
            frames_dir: Directory with equirectangular frames
            output_dir: Directory for cubemap output
            run_id: Run UUID for tracing
        
        Returns:
            Number of cubemap images generated
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get cubemap settings
        cubemap_config = self.config.get('cubemap', {})
        cubemap_size = self._parse_cubemap_size(cubemap_config.get('size', '1920x1920'))
        format_type = cubemap_config.get('format', 'PNG').lower()
        quality = cubemap_config.get('quality', 'high')
        
        # Find frame files
        frame_files = (list(frames_dir.glob("*.png")) + 
                      list(frames_dir.glob("*.jpg")))
        
        if not frame_files:
            raise Exception(f"No frames found in {frames_dir}")
        
        frame_files.sort()
        
        input_ext = frame_files[0].suffix
        output_ext = '.png' if format_type == 'png' else '.jpg'
        
        logger.info(f"Generating {cubemap_size}x{cubemap_size} cubemap from {len(frame_files)} frames",
                   extra={"run_id": run_id})
        
        generated = 0
        skipped = 0
        
        for frame_file in frame_files:
            frame_name = frame_file.stem
            
            # Check if all directions already exist for this frame
            all_exist = all(
                (output_dir / f"{frame_name}_{dir_name}{output_ext}").exists()
                for dir_name, _, _ in self.DIRECTIONS
            )
            
            if all_exist:
                skipped += len(self.DIRECTIONS)
                continue
            
            # Generate cubemap faces for this frame
            for dir_name, yaw, pitch in self.DIRECTIONS:
                output_file = output_dir / f"{frame_name}_{dir_name}{output_ext}"
                
                if is_completed(output_file):
                    skipped += 1
                    continue
                
                self._generate_face(
                    frame_file, output_file, yaw, pitch,
                    cubemap_size, format_type, quality, run_id
                )
                
                write_ok_and_sha(output_file)
                generated += 1
            
            if (generated + skipped) % 50 == 0:
                logger.info(f"Progress: {generated + skipped} images processed",
                           extra={"run_id": run_id})
        
        logger.info(f"Cubemap complete: {generated} new, {skipped} skipped",
                   extra={"run_id": run_id})
        return generated
    
    def _generate_face(self, input_file: Path, output_file: Path, 
                       yaw: int, pitch: int, size: int, 
                       format_type: str, quality: str, run_id: str):
        """Generate a single cubemap face."""
        cmd = [
            self.ffmpeg_path,
            '-i', str(input_file),
            '-vf', f'v360=equirect:rectilinear:yaw={yaw}:pitch={pitch}:h_fov=90:v_fov=90:w={size}:h={size}',
        ]
        
        if format_type == 'png':
            cmd.extend(['-pix_fmt', 'rgb24'])
        else:
            quality_value = self._get_quality_value(quality)
            cmd.extend(['-q:v', quality_value])
        
        cmd.extend(['-map_metadata', '-1', '-y', str(output_file)])
        
        run_subprocess(cmd, timeout=90, run_id=run_id)
    
    def _parse_cubemap_size(self, size_str: str) -> int:
        """Parse cubemap size string."""
        try:
            return int(size_str.split('x')[0])
        except:
            return 1920  # Default
    
    def _get_quality_value(self, quality: str) -> str:
        """Convert quality to FFmpeg parameter."""
        quality_map = {'high': '1', 'medium': '4', 'low': '8'}
        return quality_map.get(quality.lower(), '2')