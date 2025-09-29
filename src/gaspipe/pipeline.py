#!/usr/bin/env python3
"""Main pipeline orchestration."""
import logging
from pathlib import Path
from datetime import datetime, UTC
import uuid

from .types import ProjectCheckpoint, ManifestEntry
from .config import load_config
from .io_helpers import atomic_write

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
    
    logger.info(f"Starting pipeline run {run_id}")
    
    # Load configuration
    config = load_config(config_file)
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "frames").mkdir(exist_ok=True)
    (output_dir / "cubemap_images").mkdir(exist_ok=True)
    (output_dir / "realitycapture_output").mkdir(exist_ok=True)
    (output_dir / "gaussian_splat").mkdir(exist_ok=True)
    (output_dir / "logs").mkdir(exist_ok=True)
    
    # Initialize checkpoint
    checkpoint = ProjectCheckpoint(
        run_id=run_id,
        video_file=video_file,
        output_dir=output_dir,
        current_step="frames",
        manifest=[
            ManifestEntry(
                step="frames",
                status="pending",
                started_at=datetime.now(UTC)
            ),
            ManifestEntry(
                step="cubemap",
                status="pending",
                started_at=datetime.now(UTC)
            ),
            ManifestEntry(
                step="realitycapture",
                status="pending",
                started_at=datetime.now(UTC)
            ),
            ManifestEntry(
                step="postshot",
                status="pending",
                started_at=datetime.now(UTC)
            )
        ],
        config_snapshot=config,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )
    
    # Save initial checkpoint
    checkpoint_path = output_dir / "checkpoint.json"
    atomic_write(checkpoint_path, checkpoint.model_dump_json(indent=2))
    
    logger.info("Pipeline initialization complete")
    logger.warning("STUB: Full pipeline implementation in progress")
    
    # TODO: Implement actual pipeline steps
    # - Extract frames (video_processor.py)
    # - Generate cubemap (cubemap_generator.py)
    # - Process with RealityCapture (reality_capture.py)
    # - Train with PostShot (postshot_trainer.py)


def resume_pipeline(checkpoint: ProjectCheckpoint) -> None:
    """
    Resume pipeline from checkpoint.
    
    Args:
        checkpoint: Loaded checkpoint object
    """
    logger.info(f"Resuming pipeline {checkpoint.run_id} from {checkpoint.current_step}")
    
    next_step = checkpoint.get_next_step()
    
    if next_step is None:
        logger.info("Pipeline already completed")
        return
    
    logger.warning(f"STUB: Resume from {next_step} - implementation in progress")
    
    # TODO: Implement resume logic
    # - Load checkpoint state
    # - Skip completed steps
    # - Continue from next_step