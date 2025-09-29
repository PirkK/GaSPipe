#!/usr/bin/env python3
"""Main pipeline orchestration - COMPLETE IMPLEMENTATION."""
import logging
from pathlib import Path
from datetime import datetime, UTC
import uuid

from .types import ProjectCheckpoint, ManifestEntry
from .config import load_config
from .io_helpers import atomic_write
from .video_processor import VideoProcessor
from .cubemap_generator import CubemapGenerator
from .reality_capture import RealityCaptureProcessor
from .postshot_trainer import PostShotTrainer

logger = logging.getLogger(__name__)


def run_pipeline(
    video_file: Path,
    output_dir: Path,
    config_file: Path | None = None,
    run_id: str | None = None
) -> None:
    """
    Execute complete GaSPipe pipeline.
    
    Args:
        video_file: Input 360° video file
        output_dir: Output directory for all artifacts
        config_file: Optional configuration file
        run_id: Optional run UUID for tracing
    """
    if run_id is None:
        run_id = str(uuid.uuid4())
    
    logger.info(f"Starting pipeline run {run_id}", extra={"run_id": run_id})
    
    # Load configuration
    config = load_config(config_file)
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    cubemap_dir = output_dir / "cubemap_images"
    rc_dir = output_dir / "realitycapture_output"
    splat_dir = output_dir / "gaussian_splat"
    logs_dir = output_dir / "logs"
    
    for d in [frames_dir, cubemap_dir, rc_dir, splat_dir, logs_dir]:
        d.mkdir(exist_ok=True)
    
    # Initialize checkpoint
    checkpoint = ProjectCheckpoint(
        run_id=run_id,
        video_file=video_file,
        output_dir=output_dir,
        current_step="frames",
        manifest=[
            ManifestEntry(step="frames", status="pending", started_at=datetime.now(UTC)),
            ManifestEntry(step="cubemap", status="pending", started_at=datetime.now(UTC)),
            ManifestEntry(step="realitycapture", status="pending", started_at=datetime.now(UTC)),
            ManifestEntry(step="postshot", status="pending", started_at=datetime.now(UTC))
        ],
        config_snapshot=config,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    checkpoint_path = output_dir / "checkpoint.json"
    _save_checkpoint(checkpoint, checkpoint_path)
    
    # Initialize processors
    video_proc = VideoProcessor(config)
    cubemap_gen = CubemapGenerator(config)
    rc_proc = RealityCaptureProcessor(config)
    postshot_trainer = PostShotTrainer(config)
    
    try:
        # STEP 1: Extract Frames
        logger.info("Step 1/4: Extracting frames", extra={"run_id": run_id})
        _update_step_status(checkpoint, "frames", "running")
        _save_checkpoint(checkpoint, checkpoint_path)
        
        frame_count = video_proc.extract_frames(video_file, frames_dir, run_id)
        
        _update_step_status(checkpoint, "frames", "completed", 
                           outputs=[frames_dir], 
                           meta={"frame_count": frame_count})
        checkpoint.current_step = "cubemap"
        _save_checkpoint(checkpoint, checkpoint_path)
        
        # STEP 2: Generate Cubemap
        logger.info("Step 2/4: Generating cubemap", extra={"run_id": run_id})
        _update_step_status(checkpoint, "cubemap", "running")
        _save_checkpoint(checkpoint, checkpoint_path)
        
        cubemap_count = cubemap_gen.generate_cubemap(frames_dir, cubemap_dir, run_id)
        
        _update_step_status(checkpoint, "cubemap", "completed",
                           outputs=[cubemap_dir],
                           meta={"cubemap_count": cubemap_count})
        checkpoint.current_step = "realitycapture"
        _save_checkpoint(checkpoint, checkpoint_path)
        
        # STEP 3: RealityCapture Processing
        logger.info("Step 3/4: RealityCapture processing", extra={"run_id": run_id})
        _update_step_status(checkpoint, "realitycapture", "running")
        _save_checkpoint(checkpoint, checkpoint_path)
        
        rc_output = rc_proc.process_images(cubemap_dir, rc_dir, run_id)
        
        _update_step_status(checkpoint, "realitycapture", "completed",
                           outputs=[rc_output['sparse_ply'], rc_output['poses_csv']],
                           meta={"pose_count": rc_output['pose_count']})
        checkpoint.current_step = "postshot"
        _save_checkpoint(checkpoint, checkpoint_path)
        
        # STEP 4: PostShot Training
        logger.info("Step 4/4: PostShot training", extra={"run_id": run_id})
        _update_step_status(checkpoint, "postshot", "running")
        _save_checkpoint(checkpoint, checkpoint_path)
        
        video_name = video_file.stem
        postshot_output = postshot_trainer.train(cubemap_dir, rc_output, splat_dir, video_name, run_id)
        
        _update_step_status(checkpoint, "postshot", "completed",
                           outputs=[postshot_output['project_file']],
                           meta={"file_size": postshot_output['file_size']})
        checkpoint.current_step = "completed"
        _save_checkpoint(checkpoint, checkpoint_path)
        
        logger.info("Pipeline completed successfully!", extra={"run_id": run_id})
        
    except Exception as e:
        # Mark current step as failed
        current_step = checkpoint.current_step
        _update_step_status(checkpoint, current_step, "failed", error=str(e))
        _save_checkpoint(checkpoint, checkpoint_path)
        logger.error(f"Pipeline failed at step {current_step}", extra={"run_id": run_id}, exc_info=True)
        raise


def resume_pipeline(checkpoint: ProjectCheckpoint) -> None:
    """
    Resume pipeline from checkpoint.
    
    Args:
        checkpoint: Loaded checkpoint object
    """
    run_id = checkpoint.run_id
    logger.info(f"Resuming pipeline {run_id} from {checkpoint.current_step}", extra={"run_id": run_id})
    
    next_step = checkpoint.get_next_step()
    
    if next_step is None:
        logger.info("Pipeline already completed", extra={"run_id": run_id})
        return
    
    # Reload config and create processors
    config = checkpoint.config_snapshot
    output_dir = checkpoint.output_dir
    
    video_proc = VideoProcessor(config)
    cubemap_gen = CubemapGenerator(config)
    rc_proc = RealityCaptureProcessor(config)
    postshot_trainer = PostShotTrainer(config)
    
    checkpoint_path = output_dir / "checkpoint.json"
    
    # Define directories
    frames_dir = output_dir / "frames"
    cubemap_dir = output_dir / "cubemap_images"
    rc_dir = output_dir / "realitycapture_output"
    splat_dir = output_dir / "gaussian_splat"
    
    try:
        # Resume from next incomplete step
        if next_step == "frames":
            logger.info("Resuming: Frame extraction", extra={"run_id": run_id})
            _update_step_status(checkpoint, "frames", "running")
            _save_checkpoint(checkpoint, checkpoint_path)
            
            frame_count = video_proc.extract_frames(checkpoint.video_file, frames_dir, run_id)
            
            _update_step_status(checkpoint, "frames", "completed", outputs=[frames_dir])
            checkpoint.current_step = "cubemap"
            next_step = "cubemap"
        
        if next_step == "cubemap":
            logger.info("Resuming: Cubemap generation", extra={"run_id": run_id})
            _update_step_status(checkpoint, "cubemap", "running")
            _save_checkpoint(checkpoint, checkpoint_path)
            
            cubemap_count = cubemap_gen.generate_cubemap(frames_dir, cubemap_dir, run_id)
            
            _update_step_status(checkpoint, "cubemap", "completed", outputs=[cubemap_dir])
            checkpoint.current_step = "realitycapture"
            next_step = "realitycapture"
        
        if next_step == "realitycapture":
            logger.info("Resuming: RealityCapture", extra={"run_id": run_id})
            _update_step_status(checkpoint, "realitycapture", "running")
            _save_checkpoint(checkpoint, checkpoint_path)
            
            rc_output = rc_proc.process_images(cubemap_dir, rc_dir, run_id)
            
            _update_step_status(checkpoint, "realitycapture", "completed",
                               outputs=[rc_output['sparse_ply'], rc_output['poses_csv']])
            checkpoint.current_step = "postshot"
            next_step = "postshot"
        
        if next_step == "postshot":
            logger.info("Resuming: PostShot training", extra={"run_id": run_id})
            _update_step_status(checkpoint, "postshot", "running")
            _save_checkpoint(checkpoint, checkpoint_path)
            
            # Load RC outputs
            rc_output = {
                'sparse_ply': rc_dir / "sparse_points.ply",
                'poses_csv': rc_dir / "camera_poses.csv",
                'pose_count': 0  # Will be recalculated
            }
            
            video_name = checkpoint.video_file.stem
            postshot_output = postshot_trainer.train(cubemap_dir, rc_output, splat_dir, video_name, run_id)
            
            _update_step_status(checkpoint, "postshot", "completed",
                               outputs=[postshot_output['project_file']])
            checkpoint.current_step = "completed"
        
        _save_checkpoint(checkpoint, checkpoint_path)
        logger.info("Resume completed successfully!", extra={"run_id": run_id})
        
    except Exception as e:
        _update_step_status(checkpoint, next_step, "failed", error=str(e))
        _save_checkpoint(checkpoint, checkpoint_path)
        logger.error(f"Resume failed at step {next_step}", extra={"run_id": run_id}, exc_info=True)
        raise


def _save_checkpoint(checkpoint: ProjectCheckpoint, path: Path):
    """Save checkpoint atomically."""
    checkpoint.updated_at = datetime.now(UTC)
    atomic_write(path, checkpoint.model_dump_json(indent=2))


def _update_step_status(checkpoint: ProjectCheckpoint, step: str, status: str, 
                       outputs: list = None, meta: dict = None, error: str = None):
    """Update manifest entry for a step."""
    for entry in checkpoint.manifest:
        if entry.step == step:
            entry.status = status
            if status == "completed":
                entry.completed_at = datetime.now(UTC)
            if outputs:
                entry.outputs = outputs
            if error:
                entry.error_message = error
            break