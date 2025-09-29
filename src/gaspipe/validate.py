#!/usr/bin/env python3
"""
Validation functions with structured error responses.
"""
import csv
from pathlib import Path
from typing import Any

from .types import FrameIndex, CameraPose, ProjectCheckpoint, ValidationError


class GaSPipeValidationError(Exception):
    """Exception wrapping structured validation error."""
    
    def __init__(self, error: ValidationError):
        self.error = error
        super().__init__(error.message)

    def to_dict(self) -> dict:
        return self.error.model_dump()


def validate_frameindex(data: dict[str, Any]) -> FrameIndex:
    """
    Validate and construct FrameIndex from raw data.
    
    Raises:
        GaSPipeValidationError: With structured error on validation failure
    """
    try:
        return FrameIndex(**data)
    except Exception as e:
        raise GaSPipeValidationError(
            ValidationError(
                code="INVALID_FRAME_INDEX",
                message=f"Frame index validation failed: {e}",
                details={"input": data, "error": str(e)}
            )
        )


def validate_camera_poses(csv_path: Path) -> list[CameraPose]:
    """
    Parse and validate camera poses from RealityCapture CSV.
    
    Expected CSV format:
    image_name,pos_x,pos_y,pos_z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal
    
    Raises:
        GaSPipeValidationError: If CSV malformed or poses invalid
    """
    if not csv_path.exists():
        raise GaSPipeValidationError(
            ValidationError(
                code="POSES_FILE_NOT_FOUND",
                message=f"Camera poses file not found: {csv_path}",
                details={"path": str(csv_path)}
            )
        )

    poses = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=1):
                try:
                    pose = CameraPose(
                        image_name=row['image_name'],
                        position=(
                            float(row['pos_x']),
                            float(row['pos_y']),
                            float(row['pos_z'])
                        ),
                        rotation=[
                            [float(row['r00']), float(row['r01']), float(row['r02'])],
                            [float(row['r10']), float(row['r11']), float(row['r12'])],
                            [float(row['r20']), float(row['r21']), float(row['r22'])]
                        ],
                        focal_length=float(row['focal'])
                    )
                    poses.append(pose)
                except (KeyError, ValueError) as e:
                    raise GaSPipeValidationError(
                        ValidationError(
                            code="INVALID_POSE_ROW",
                            message=f"Invalid pose at row {row_num}: {e}",
                            details={"row": row_num, "data": row, "error": str(e)}
                        )
                    )
    except csv.Error as e:
        raise GaSPipeValidationError(
            ValidationError(
                code="CSV_PARSE_ERROR",
                message=f"Failed to parse CSV: {e}",
                details={"path": str(csv_path), "error": str(e)}
            )
        )

    if not poses:
        raise GaSPipeValidationError(
            ValidationError(
                code="NO_POSES_FOUND",
                message="No valid camera poses found in CSV",
                details={"path": str(csv_path)}
            )
        )

    return poses


def validate_checkpoint(checkpoint_path: Path) -> ProjectCheckpoint:
    """
    Load and validate project checkpoint JSON.
    
    Raises:
        GaSPipeValidationError: If checkpoint invalid or corrupted
    """
    if not checkpoint_path.exists():
        raise GaSPipeValidationError(
            ValidationError(
                code="CHECKPOINT_NOT_FOUND",
                message=f"Checkpoint file not found: {checkpoint_path}",
                details={"path": str(checkpoint_path)}
            )
        )

    try:
        import json
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        return ProjectCheckpoint(**data)
    except json.JSONDecodeError as e:
        raise GaSPipeValidationError(
            ValidationError(
                code="CHECKPOINT_CORRUPT",
                message=f"Checkpoint JSON corrupted: {e}",
                details={"path": str(checkpoint_path), "error": str(e)}
            )
        )
    except Exception as e:
        raise GaSPipeValidationError(
            ValidationError(
                code="CHECKPOINT_INVALID",
                message=f"Checkpoint validation failed: {e}",
                details={"path": str(checkpoint_path), "error": str(e)}
            )
        )