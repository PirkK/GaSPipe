#!/usr/bin/env python3
"""
Pydantic models for GaSPipe pipeline type safety.
"""
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class FrameIndex(BaseModel):
    """Represents a single extracted video frame."""
    
    frame_number: int = Field(ge=0, description="Zero-indexed frame number")
    timestamp_sec: float = Field(ge=0.0, description="Timestamp in video")
    file_path: Path = Field(description="Absolute path to frame file")
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$', description="SHA256 checksum")

    class Config:
        frozen = True  # Immutable after creation


class CameraPose(BaseModel):
    """Camera pose from RealityCapture registration."""
    
    image_name: str = Field(min_length=1)
    position: tuple[float, float, float] = Field(description="XYZ position in meters")
    rotation: list[list[float]] = Field(description="3x3 rotation matrix")
    focal_length: float = Field(gt=0, description="Focal length in mm")

    class Config:
        frozen = True


class ManifestEntry(BaseModel):
    """Single pipeline step manifest entry."""
    
    step: Literal["frames", "cubemap", "realitycapture", "postshot"]
    status: Literal["pending", "running", "completed", "failed"]
    started_at: datetime
    completed_at: Optional[datetime] = None
    outputs: list[Path] = Field(default_factory=list)
    sha256_sums: dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ProjectCheckpoint(BaseModel):
    """Complete project checkpoint for resume capability."""
    
    run_id: str = Field(pattern=r'^[a-f0-9\-]{36}$', description="UUID4 run identifier")
    video_file: Path
    output_dir: Path
    current_step: str
    manifest: list[ManifestEntry]
    config_snapshot: dict
    created_at: datetime
    updated_at: datetime

    def get_next_step(self) -> Optional[str]:
        """Return next step to execute, or None if complete."""
        step_order = ["frames", "cubemap", "realitycapture", "postshot"]
        for entry in self.manifest:
            if entry.status != "completed":
                return entry.step
        return None


class ValidationError(BaseModel):
    """Structured validation error response."""
    
    code: str = Field(pattern=r'^[A-Z_]+$')
    message: str
    details: dict = Field(default_factory=dict)