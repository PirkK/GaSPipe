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

```python
class FrameIndex(BaseModel):
    frame_number: int = Field(ge=0)
    timestamp_sec: float = Field(ge=0.0)
    file_path: Path
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

class CameraPose(BaseModel):
    image_name: str
    position: tuple[float, float, float]
    rotation: list[list[float]]  # 3x3 matrix
    focal_length: float = Field(gt=0)

class ManifestEntry(BaseModel):
    step: Literal["frames", "cubemap", "realitycapture", "postshot"]
    status: Literal["pending", "running", "completed", "failed"]
    started_at: datetime
    completed_at: Optional[datetime] = None
    outputs: list[Path] = []
    sha256_sums: dict[str, str] = {}
    error_message: Optional[str] = None

class ProjectCheckpoint(BaseModel):
    run_id: str
    video_file: Path
    output_dir: Path
    current_step: str
    manifest: list[ManifestEntry]
    config_snapshot: dict
    created_at: datetime
    updated_at: datetime
```

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

```json
{
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
```

## Log Format (JSON)

```json
{
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
```

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

```json
{
  "code": "INVALID_FRAME_INDEX",
  "message": "Frame number must be non-negative",
  "details": {
    "field": "frame_number",
    "value": -5,
    "constraint": "ge=0"
  }
}
```

## Subprocess Environment Propagation

All subprocess calls receive:
- `GASPIPE_RUN_ID`: Current run UUID
- Parent environment variables (PATH, etc.)

## Pipeline Steps

### Step 1: Frame Extraction (video_processor.py)

**Input**: 360° equirectangular video (MP4, AVI, MOV, MKV)  
**Output**: Individual frames (PNG/JPG)

**Process**:
```python
ffmpeg -i input.mp4 \
  -vf "fps=1,scale=3840:1920,format=rgb24,colorspace=bt709" \
  -pix_fmt rgb24 \
  output/frames/frame_%06d.png
```

**Configurable**:
- FPS: 0.5 - 10.0
- Resolution: 8K, 4K, 2K, FullHD
- Format: PNG (lossless) or JPG (quality: high/medium/low)

**Resume**: Checks for `.ok` markers, skips existing frames

---

### Step 2: Cubemap Generation (cubemap_generator.py)

**Input**: Equirectangular frames  
**Output**: 9-direction cubemap images per frame

**Directions**:
1. front (0°, 0°)
2. right (90°, 0°)
3. back (180°, 0°)
4. left (-90°, 0°)
5. front_right (45°, 0°)
6. back_right (135°, 0°)
7. back_left (-135°, 0°)
8. front_left (-45°, 0°)
9. top (0°, 90°)

**Process (per direction)**:
```python
ffmpeg -i frame.png \
  -vf "v360=equirect:rectilinear:yaw=0:pitch=0:h_fov=90:v_fov=90:w=1920:h=1920" \
  -map_metadata -1 \
  frame_front.png
```

**Configurable**:
- Cubemap size: 1920x1920, 960x960
- Format: PNG or JPG
- Quality: high/medium/low

**Resume**: Checks each cubemap face individually

---

### Step 3: RealityCapture (reality_capture.py)

**Input**: Cubemap images  
**Output**: Sparse 3D point cloud + Camera poses CSV

**Process**:
```bash
RealityCapture.exe \
  -addFolder cubemap_images/ \
  -align \
  -selectMaximalComponent \
  -calculateNormalModel \
  -exportSparsePointCloud sparse_points.ply \
  -exportRegistration camera_poses.csv \
  -save project.rcproj \
  -quit
```

**Output Files**:
- `sparse_points.ply`: 3D point cloud (PLY format)
- `camera_poses.csv`: Camera positions + rotations (CSV)

**CSV Format**:
```csv
image_name,pos_x,pos_y,pos_z,r00,r01,r02,r10,r11,r12,r20,r21,r22,focal
img_001.png,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,50.0
```

**Resume**: Checks for valid PLY (>1KB) and CSV (>100 bytes)

**Known Fix**: CSV header skipping in `_count_poses()` to avoid counting header as pose

---

### Step 4: PostShot Training (postshot_trainer.py)

**Input**: 
- Cubemap images
- RealityCapture outputs (PLY + CSV)

**Output**: Gaussian Splat project (.psht)

**Process**:
```bash
postshot-cli train \
  --import images/ \
  --output project.psht \
  --profile "Splat MCMC" \
  -s 25 \
  --max-image-size 0
```

**Configurable**:
- Profile: Splat MCMC, Splat Standard
- Training steps: 10-50k (in thousands)

**Resume**: Checks for valid .psht file (>1MB)

**Known Fix**: Recalculates pose count from CSV during resume

---

## Recent Bug Fixes (v0.1.0)

### Fix 1: CSV Header Counting Bug

**Issue**: `_count_poses()` in `reality_capture.py` was counting CSV header as a pose

**Before**:
```python
def _count_poses(self, csv_path: Path) -> int:
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        return sum(1 for row in reader if row and len(row) > 10)
    # ❌ Counts header row
```

**After**:
```python
def _count_poses(self, csv_path: Path) -> int:
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        next(reader, None)  # ✅ Skip header
        return sum(1 for row in reader if row and len(row) > 10)
```

---

### Fix 2: Resume Pose Count Bug

**Issue**: `resume_pipeline()` in `pipeline.py` wasn't recalculating pose count from CSV

**Before**:
```python
rc_output = {
    'sparse_ply': rc_dir / "sparse_points.ply",
    'poses_csv': rc_dir / "camera_poses.csv",
    'pose_count': 0  # ❌ Always 0 on resume
}
```

**After**:
```python
poses_csv_path = rc_dir / "camera_poses.csv"
rc_output = {
    'sparse_ply': rc_dir / "sparse_points.ply",
    'poses_csv': poses_csv_path,
    'pose_count': rc_proc._count_poses(poses_csv_path)  # ✅ Recalculates
}
```

---

## Performance Considerations

### Bottlenecks

1. **Cubemap Generation**: Sequential processing of frames
   - **Solution**: Parallelize with `multiprocessing.Pool`
   - **Impact**: 4-8x speedup on multi-core systems

2. **RealityCapture**: Single-threaded alignment
   - **Mitigation**: Reduce image count (lower FPS)
   - **Alternative**: GPU-accelerated alignment settings

3. **PostShot Training**: GPU memory limited
   - **Optimization**: Batch size tuning
   - **Trade-off**: Steps vs quality

### Optimization Roadmap

**Phase 1** (Current): Sequential, reliable
**Phase 2**: Parallel cubemap generation
**Phase 3**: Async logging
**Phase 4**: Distributed processing (multiple GPUs)

---

## Testing Strategy

### Unit Tests (31 tests)
- Mock all subprocess calls
- Test retry logic
- Validate Pydantic models
- Test atomic I/O operations

### Integration Tests
- Full pipeline with mocked software
- Resume from various checkpoints
- Error handling scenarios

### E2E Tests (Manual)
- Real 360° videos
- Actual FFmpeg/RC/PostShot
- Performance benchmarking

---

## Security Model

1. **Input Validation**: All paths normalized via `pathlib.Path`
2. **No Shell Injection**: Subprocess calls use list format
3. **Checksum Verification**: SHA256 for all outputs
4. **Atomic Operations**: No partial states
5. **Least Privilege**: No elevated permissions needed

---

## Future Enhancements

### Planned Features
- [ ] Web UI for monitoring
- [ ] Real-time progress bars
- [ ] Automatic cleanup of intermediates
- [ ] Distributed processing support
- [ ] Cloud storage integration (S3, GCS)
- [ ] Quality metrics reporting

### Under Consideration
- [ ] Alternative to RealityCapture (COLMAP integration)
- [ ] Multiple Gaussian Splat backends
- [ ] Video streaming input
- [ ] Interactive checkpoint editor

---

**Version**: 0.1.0  
**Last Updated**: 2025-09-29  
**Maintainer**: TwiceOut Team