#!/usr/bin/env python3
"""
Video frame extraction from 360° videos using FFmpeg.
"""
import logging
from pathlib import Path

from .subprocess_wrapper import run_subprocess
from .io_helpers import write_ok_and_sha, is_completed

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Extract frames from 360° video files."""
    
    def __init__(self, config: dict):
        self.config = config
        self.ffmpeg_path = config.get('ffmpeg_path', 'ffmpeg')
    
    def extract_frames(self, video_file: Path, output_dir: Path, run_id: str) -> int:
        """
        Extract frames from video file.
        
        Args:
            video_file: Input 360° video file
            output_dir: Directory for output frames
            run_id: Run UUID for tracing
        
        Returns:
            Number of frames extracted
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get video settings
        video_config = self.config.get('video', {})
        fps = video_config.get('fps', 1.0)
        resolution = video_config.get('resolution', '4K')
        format_type = video_config.get('format', 'PNG').lower()
        quality = video_config.get('quality', 'high')
        
        # Parse resolution
        width, height = self._parse_resolution(resolution)
        
        # Output format
        output_ext = '.png' if format_type == 'png' else '.jpg'
        output_pattern = str(output_dir / f"frame_%06d{output_ext}")
        
        logger.info(f"Extracting frames: {width}x{height}, {fps} FPS, {format_type.upper()}", 
                   extra={"run_id": run_id})
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            '-i', str(video_file),
            '-vf', f'fps={fps},scale={width}:{height},format=rgb24,colorspace=bt709',
        ]
        
        # Format-specific options
        if format_type == 'png':
            cmd.extend(['-pix_fmt', 'rgb24'])
        else:
            quality_value = self._get_quality_value(quality)
            cmd.extend(['-q:v', quality_value])
        
        cmd.extend(['-y', output_pattern])
        
        # Execute FFmpeg
        try:
            run_subprocess(cmd, timeout=3600, run_id=run_id)
            
            # Count extracted frames
            frame_files = list(output_dir.glob(f"*{output_ext}"))
            frame_count = len(frame_files)
            
            # Mark frames as completed
            for frame_file in frame_files:
                if not is_completed(frame_file):
                    write_ok_and_sha(frame_file)
            
            logger.info(f"Extracted {frame_count} frames", extra={"run_id": run_id})
            return frame_count
            
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}", extra={"run_id": run_id})
            raise
    
    def _parse_resolution(self, resolution: str) -> tuple[int, int]:
        """Parse resolution string to width/height."""
        resolution_map = {
            '8K': (7680, 3840),
            '4K': (3840, 1920),
            '2K': (2048, 1024),
            'FullHD': (1920, 960)
        }
        
        for key, (w, h) in resolution_map.items():
            if key in resolution:
                return w, h
        
        # Default to 4K
        return 3840, 1920
    
    def _get_quality_value(self, quality: str) -> str:
        """Convert quality setting to FFmpeg parameter."""
        quality_map = {
            'high': '2',
            'medium': '5',
            'low': '8'
        }
        return quality_map.get(quality.lower(), '2')
    
    def validate_video(self, video_file: Path) -> tuple[bool, str]:
        """
        Validate video file is suitable for processing.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not video_file.exists():
            return False, "Video file does not exist"
        
        if not video_file.is_file():
            return False, "Path is not a file"
        
        valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        if video_file.suffix.lower() not in valid_extensions:
            return False, f"Unsupported format: {video_file.suffix}"
        
        if video_file.stat().st_size < 1024 * 1024:  # 1MB minimum
            return False, "Video file too small (may be corrupted)"
        
        return True, "Valid video file"