from pydantic import BaseModel
from typing import List, Optional, Tuple

class FrameIndex(BaseModel):
    video_id: str
    frame_count: int
    fps: float
    resolution: Tuple[int,int]
    files: List[str]

class CameraPose(BaseModel):
    image: str
    tx: float
    ty: float
    tz: float
    qx: float
    qy: float
    qz: float
    qw: float
    confidence: Optional[float] = None

class ProjectCheckpoint(BaseModel):
    project_id: str
    run_id: str
    completed_steps: List[str]
    current_step: Optional[str]
    errors: List[dict] = []
    timestamp: float
