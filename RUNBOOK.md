# GaSPipe Operations Runbook

## Quick Diagnostics

### Extract Logs for Error Tracing
```bash
# Filter logs by run_id
jq 'select(.run_id=="<RUN_ID>")' output/logs/*.log

# Extract errors only
jq 'select(.level=="ERROR")' output/logs/*.log

# View subprocess failures
jq 'select(.meta.stderr)' output/logs/*.log

export LOG_LEVEL=DEBUG
python -m src.gaspipe.cli run input.mp4 output/ --log-level DEBUG

# FFmpeg
ffmpeg -version

# RealityCapture (check path)
$RC_CLI_PATH -help

# PostShot
$POSTSHOT_CLI_PATH --help

# Full self-test
python -m src.gaspipe.cli self-test \
  --rc-path=$RC_CLI_PATH \
  --postshot-path=$POSTSHOT_CLI_PATH

# View checkpoint
jq '.' output/checkpoint.json

# Find failed step
jq '.manifest[] | select(.status!="completed")' output/checkpoint.json

python -m src.gaspipe.cli resume output/

# Remove .ok markers to force regeneration
find output/ -name "*.ok" -delete

# Verify integrity before resume
find output/ -name "*.sha256" -exec bash -c \
  'sha256sum -c {} || echo "CORRUPT: {}"' \;

# Find .psht files
find output/gaussian_splat -name "*.psht"

# Check file sizes
du -sh output/gaussian_splat/*.psht

# Frames
ls -lh output/frames/ | head

# Cubemap images
ls -lh output/cubemap_images/ | head

# RealityCapture sparse cloud
ls -lh output/realitycapture_output/sparse_points.ply

# Camera poses
wc -l output/realitycapture_output/camera_poses.csv

docker images gaspipe --format "{{.Tag}}"

# Tag current as backup
docker tag gaspipe:latest gaspipe:latest-backup

# Pull specific version
docker tag gaspipe:<GIT_SHA> gaspipe:latest

# Verify version
docker run --rm gaspipe:latest self-test

jq '.' output/checkpoint.json || echo "INVALID JSON"

# Restore from backup (if exists)
cp output/checkpoint.json.bak output/checkpoint.json

# Or restart from beginning
rm output/checkpoint.json
python -m src.gaspipe.cli run input.mp4 output/

ls -l output/realitycapture_output/
jq '.manifest[] | select(.step=="realitycapture")' output/checkpoint.json

# Remove RealityCapture .ok markers
rm output/realitycapture_output/*.ok

# Resume pipeline
python -m src.gaspipe.cli resume output/

# Check running processes
ps aux | grep -E 'ffmpeg|RealityCapture|postshot'

# View recent log entries
tail -f output/logs/*.log | jq 'select(.message | contains("timeout"))'

# Increase timeout (requires code change in config)
# Or split processing into smaller chunks

# For PostShot timeout, reduce training steps:
# Edit config: "trainsteps": 10  # instead of 25

# Watch checkpoint updates
watch -n 5 'jq ".current_step" output/checkpoint.json'

# Monitor log file growth
watch -n 10 'ls -lh output/logs/*.log'

# View step timestamps
jq '.manifest[] | {step, started: .started_at, completed: .completed_at}' \
  output/checkpoint.json

# Calculate average step duration (manual)

# Check available space
df -h output/

# Clean intermediate files after success
find output/frames -name "*.ok" -delete
find output/frames -name "*.png" -delete  # Keep only manifest

# Monitor during execution
while true; do
  ps aux | grep -E 'python|ffmpeg|RealityCapture' | \
    awk '{sum+=$6} END {print sum/1024 " MB"}'
  sleep 5
done

---

## 7. REPOSITORY STRUCTURE

gaspipe/
├── .github/
│   └── workflows/
│       └── ci.yml                    # CI/CD pipeline
├── docs/
│   ├── design.md                     # Architecture design doc
│   └── API.md                        # (Future) API documentation
├── scripts/
│   ├── mock_rc_cli.py               # Mock RealityCapture for tests
│   └── mock_postshot_cli.py         # Mock PostShot for tests
├── src/
│   └── gaspipe/
│       ├── init.py
│       ├── cli.py                   # CLI entry point
│       ├── types.py                 # Pydantic models
│       ├── validate.py              # Validation functions
│       ├── subprocess_wrapper.py    # Subprocess runner with retry
│       ├── logging_config.py        # JSON logging setup
│       ├── io_helpers.py            # Atomic file operations
│       ├── config.py                # Configuration loader
│       ├── pipeline.py              # Main pipeline orchestration
│       ├── video_processor.py       # FFmpeg frame extraction
│       ├── cubemap_generator.py     # Cubemap generation
│       ├── reality_capture.py       # RealityCapture integration
│       └── postshot_trainer.py      # PostShot training
├── tests/
│   ├── init.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_types.py                # Type model tests
│   ├── test_validate.py             # Validation tests
│   ├── test_subprocess_wrapper.py   # Subprocess wrapper tests
│   ├── test_io_helpers.py           # I/O helpers tests
│   ├── test_logging_config.py       # Logging tests
│   ├── test_pipeline_integration.py # End-to-end integration tests
│   └── fixtures/
│       ├── config.json              # Test configuration
│       └── mini360.mp4              # Minimal test video
├── .gitignore
├── .ruff.toml                       # Ruff configuration
├── Dockerfile
├── LICENSE
├── README.md
├── RUNBOOK.md
├── requirements.txt
└── pyproject.toml                   # Python project metadata

---

## 8. GIT WORKFLOW & PR INSTRUCTIONS

### Branch Creation & Commits
```bash
# Create feature branches
git checkout -b feat/validate-subproc-logging
git checkout -b test/integration-fixtures
git checkout -b ci/docker

# Apply patches (example for types.py)
# Save diff to file, then:
git apply patches/types.py.patch

# Commit with conventional commits
git add src/gaspipe/types.py
git commit -m "feat(types): add Pydantic models FrameIndex CameraPose ProjectCheckpoint

- Define immutable data models with validation
- Add ValidationError for structured error responses
- Enable type safety at module boundaries

Refs: #1"

# More commits following pattern
git commit -m "feat(validate): implement structured validation with JSON errors"
git commit -m "feat(subprocess): add retry wrapper with exponential backoff"
git commit -m "feat(logging): implement JSON structured logging with run_id"
git commit -m "feat(io): add atomic file operations with SHA256 checksums"
git commit -m "feat(cli): implement CLI with run/resume/validate commands"

# Push branch
git push -u origin feat/validate-subproc-logging

