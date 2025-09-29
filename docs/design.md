# GaSPipe Architecture Design

## Overview
Automated pipeline: 360° Video → Frames → Cubemap → RealityCapture → PostShot → Gaussian Splats (.psht)

## Core Principles
1. **Idempotency**: All operations resumable via `.ok` markers and manifest tracking
2. **Atomicity**: File writes are atomic; checkpoint updates transactional
3. **Observability**: JSON structured logs with `run_id` for tracing
4. **Validation**: Pydantic models enforce contracts at boundaries
5. **Resilience**: Subprocess wrapper with exponential backoff retry

## Data Models (Pydantic)
```pythonclass FrameIndex(BaseModel):
frame_number: int = Field(ge=0)
timestamp_sec: float = Field(ge=0.0)
file_path: Path
sha256: str = Field(pattern=r'^[a-f0-9]{64}$')class CameraPose(BaseModel):
image_name: str
position: tuple[float, float, float]
rotation: list[list[float]]  # 3x3 matrix
focal_length: float = Field(gt=0)class ManifestEntry(BaseModel):
step: Literal["frames", "cubemap", "realitycapture", "postshot"]
status: Literal["pending", "running", "completed", "failed"]
started_at: datetime
completed_at: Optional[datetime] = None
outputs: list[Path] = []
sha256_sums: dict[str, str] = {}class ProjectCheckpoint(BaseModel):
run_id: str
video_file: Path
output_dir: Path
current_step: str
manifest: list[ManifestEntry]
config_snapshot: dict
created_at: datetime
updated_at: datetime

## Checkpoint Flow

1. **Initialization**: Create `checkpoint.json` with `run_id`, initial manifest (all `pending`)
2. **Step Execution**:
   - Update step status to `running`
   - Write atomic checkpoint
   - Execute operation
   - Create `.ok` + `.sha256` for outputs
   - Update manifest with outputs/checksums
   - Update step status to `completed`
   - Write final checkpoint
3. **Resume**: Load checkpoint, identify first non-`completed` step, continue from there

## Manifest Schema
```json{
"run_id": "uuid4-string",
"video_file": "/path/to/input.mp4",
"output_dir": "/path/to/output",
"current_step": "cubemap",
"manifest": [
{
"step": "frames",
"status": "completed",
"started_at": "2025-01-15T10:00:00Z",
"completed_at": "2025-01-15T10:05:00Z",
"outputs": ["/path/to/output/frames/frame_0001.png"],
"sha256_sums": {"frame_0001.png": "abc123..."}
}
],
"config_snapshot": {...},
"created_at": "2025-01-15T10:00:00Z",
"updated_at": "2025-01-15T10:05:00Z"
}

## Log Format (JSON)
```json{
"timestamp": "2025-01-15T10:00:00.123456Z",
"level": "INFO",
"run_id": "uuid4-string",
"module": "gaspipe.video_processor",
"message": "Extracted 120 frames",
"meta": {
"duration_sec": 45.2,
"fps": 2.0,
"resolution": "3840x1920"
}
}

## Retry Policy

- **Transient Errors**: Network timeouts, temporary file locks → Retry with exponential backoff (base=2s, max=60s, max_attempts=5)
- **Permanent Errors**: Missing files, invalid arguments, process killed by OOM → Fail immediately
- **Classification**: Return code analysis + stderr pattern matching
- **Jitter**: ±25% randomization to avoid thundering herd

## Idempotency Strategy

1. **File Operations**: Check `.ok` existence before regenerating
2. **Subprocess Calls**: Verify expected outputs exist with matching SHA256
3. **Checkpoint Recovery**: Always safe to re-run; state machine prevents duplicate work
4. **Cleanup**: `.ok` removal triggers regeneration on next run

## Error Handling

All validation errors return structured JSON:
```json{
"code": "INVALID_FRAME_INDEX",
"message": "Frame number must be non-negative",
"details": {
"field": "frame_number",
"value": -5,
"constraint": "ge=0"
}
}

## Subprocess Environment Propagation

All subprocess calls receive:
- `GASPIPE_RUN_ID`: Current run UUID
- `GASPIPE_STEP`: Current pipeline step name
- Parent environment variables (PATH, etc.)