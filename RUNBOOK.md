# GaSPipe Operations Runbook

## Quick Diagnostics

### Extract Logs for Error Tracing

```bash
# Filter logs by run_id
jq 'select(.run_id=="")' output/logs/*.log

# Extract errors only
jq 'select(.level=="ERROR")' output/logs/*.log

# View subprocess failures
jq 'select(.meta.stderr)' output/logs/*.log
```

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
python -m gaspipe.cli run input.mp4 output/ --log-level DEBUG
```

---

## Software Verification

### Test All Dependencies

```bash
# FFmpeg
ffmpeg -version
ffmpeg -filters | grep v360

# RealityCapture (Windows)
"C:\Program Files\Epic Games\RealityScan_2.0\RealityScan.exe" -help

# PostShot
postshot-cli --help

# Full self-test
python -m gaspipe.cli self-test \
  --rc-path="C:/Program Files/.../RealityCapture.exe" \
  --postshot-path="C:/Program Files/.../postshot-cli.exe"
```

---

## Checkpoint Management

### View Checkpoint Status

```bash
# Current step
jq '.current_step' output/checkpoint.json

# Find failed steps
jq '.manifest[] | select(.status!="completed")' output/checkpoint.json

# All step statuses
jq '.manifest[] | {step, status}' output/checkpoint.json
```

### Resume Pipeline

```bash
python -m gaspipe.cli resume output/
```

### Force Regeneration

```bash
# Remove .ok markers to force regeneration
find output/ -name "*.ok" -delete

# Or remove specific step markers
find output/frames/ -name "*.ok" -delete
```

### Verify Integrity

```bash
# Check all SHA256 checksums
find output/ -name "*.sha256" -exec bash -c \
  'sha256sum -c {} || echo "CORRUPT: {}"' \;
```

---

## Output Validation

### Check Generated Files

```bash
# Frame count
ls output/frames/*.png | wc -l

# Cubemap count (should be frames × 9)
ls output/cubemap_images/*.png | wc -l

# Sparse point cloud size
ls -lh output/realitycapture_output/sparse_points.ply

# Camera poses count
wc -l output/realitycapture_output/camera_poses.csv

# Final Gaussian Splat
ls -lh output/gaussian_splat/*.psht
```

### Validate Outputs

```bash
# Find .psht files
find output/gaussian_splat -name "*.psht"

# Check file sizes
du -sh output/gaussian_splat/*.psht

# Verify not corrupted
file output/gaussian_splat/*.psht
```

---

## Common Issues & Solutions

### Issue: FFmpeg v360 filter not found

**Symptoms**:
```
Unknown filter 'v360'
```

**Diagnosis**:
```bash
ffmpeg -filters | grep v360
# If empty, v360 not available
```

**Solution**:
```bash
# Windows: Install FFmpeg from official site with v360
# Or use Scoop
scoop install ffmpeg

# Linux
sudo apt install ffmpeg
# Or build from source with v360 enabled
```

---

### Issue: RealityCapture fails silently

**Symptoms**:
- No camera_poses.csv or empty file
- PLY file too small (<1KB)

**Diagnosis**:
```bash
# Check RealityCapture output directory
ls -lh output/realitycapture_output/

# Check logs for RC errors
jq 'select(.module=="reality_capture") | select(.level=="ERROR")' output/logs/*.log

# Verify XML configuration
cat RC_Settings/reg_export.xml | grep calexHasDisabled
```

**Solution**:
```bash
# Ensure XML files have correct settings
# reg_export.xml should contain:
# 

# Test RealityCapture manually
RealityCapture.exe -addFolder output/cubemap_images/ -align -quit
```

---

### Issue: PostShot reports "No poses found"

**Symptoms**:
```json
{"level": "ERROR", "message": "No camera poses available"}
```

**Diagnosis**:
```bash
# Check CSV file
head output/realitycapture_output/camera_poses.csv

# Count data rows (excluding header)
tail -n +2 output/realitycapture_output/camera_poses.csv | wc -l

# Verify pose count in logs
jq 'select(.message | contains("pose"))' output/logs/*.log
```

**Solution**:
```bash
# If CSV exists but empty, RealityCapture alignment failed
# Re-run RealityCapture step:
rm output/realitycapture_output/*.ok
python -m gaspipe.cli resume output/
```

**Known Fix Applied**: `_count_poses()` now skips CSV header correctly

---

### Issue: Pipeline timeout

**Symptoms**:
```json
{"level": "ERROR", "message": "timeout", "meta": {"stderr": "..."}}
```

**Diagnosis**:
```bash
# Check running processes
ps aux | grep -E 'ffmpeg|RealityCapture|postshot'

# View recent timeout logs
tail -f output/logs/*.log | jq 'select(.message | contains("timeout"))'
```

**Solution**:
```bash
# Increase timeout in config.json
{
  "processing": {
    "timeout_minutes": 60  // Increase from default 15
  }
}

# Or for PostShot specifically, reduce training steps
{
  "postshot": {
    "steps": 10  // Reduce from 25
  }
}
```

---

### Issue: Pipeline very slow

**Symptoms**: Processing takes hours

**Diagnosis**:
```bash
# Check step durations
jq '.manifest[] | {
  step, 
  duration: ((.completed_at | fromdateiso8601) - 
             (.started_at | fromdateiso8601))
}' output/checkpoint.json
```

**Optimization Steps**:

1. **Reduce FPS**
   ```json
   {"video": {"fps": 0.5}}  // Instead of 2.0
   ```

2. **Lower Resolution**
   ```json
   {"video": {"resolution": "2K"}}  // Instead of 4K
   ```

3. **Use JPG Medium**
   ```json
   {
     "video": {"format": "JPG", "quality": "medium"},
     "cubemap": {"format": "JPG", "quality": "medium"}
   }
   ```

4. **Reduce Training Steps**
   ```json
   {"postshot": {"steps": 10}}  // Instead of 25
   ```

---

### Issue: Disk full

**Symptoms**:
```
No space left on device
```

**Diagnosis**:
```bash
# Check available space
df -h output/

# Check output sizes
du -sh output/*/
```

**Solution**:
```bash
# Clean intermediate files (after successful completion)
# Remove frames (largest)
rm -rf output/frames/

# Remove cubemap images
rm -rf output/cubemap_images/

# Keep only final outputs
# - checkpoint.json
# - gaussian_splat/*.psht
# - logs/
```

**Space Requirements** (30-second 4K video):
- Frames: ~500 MB
- Cubemap: ~3 GB
- RealityCapture: ~100 MB
- PostShot: ~500 MB
- **Total**: ~4-5 GB

---

### Issue: Resume not working

**Symptoms**: Pipeline starts from beginning

**Diagnosis**:
```bash
# Check if checkpoint exists
ls output/checkpoint.json

# Verify checkpoint is valid JSON
jq '.' output/checkpoint.json || echo "INVALID JSON"

# Check step statuses
jq '.manifest[] | {step, status}' output/checkpoint.json
```

**Solution**:
```bash
# If checkpoint corrupted, restore from backup
cp output/checkpoint.json.bak output/checkpoint.json

# Or restart from beginning
rm output/checkpoint.json
python -m gaspipe.cli run input.mp4 output/
```

---

## Performance Monitoring

### Watch Pipeline Progress

```bash
# Monitor checkpoint updates
watch -n 5 'jq ".current_step" output/checkpoint.json'

# Monitor log file growth
watch -n 10 'ls -lh output/logs/*.log'

# View step timestamps
jq '.manifest[] | {
  step, 
  started: .started_at, 
  completed: .completed_at
}' output/checkpoint.json
```

### Resource Usage

```bash
# CPU usage (Linux)
pidstat -p $PIPELINE_PID 1

# Memory usage
free -h

# Disk I/O
iostat -x 1

# GPU usage (if PostShot using GPU)
nvidia-smi -l 1
```

---

## CI/CD Troubleshooting

### Docker Build Issues

```bash
# Verify Dockerfile
docker build -t gaspipe:test .

# Check image size
docker images gaspipe --format "{{.Tag}} {{.Size}}"

# Test container
docker run --rm gaspipe:test self-test
```

### GitHub Actions Failures

```bash
# View workflow logs
gh run view 

# Download artifacts
gh run download 

# Re-run failed jobs
gh run rerun  --failed
```

---

## Maintenance Tasks

### Clean Old Logs

```bash
# Remove logs older than 7 days
find output/logs/ -name "*.log" -mtime +7 -delete

# Archive old logs
tar -czf logs_archive_$(date +%Y%m%d).tar.gz output/logs/
```

### Backup Project

```bash
# Backup entire project
tar -czf gaspipe_backup_$(date +%Y%m%d).tar.gz \
  --exclude='output/frames' \
  --exclude='output/cubemap_images' \
  output/

# Backup only essentials
tar -czf gaspipe_minimal_$(date +%Y%m%d).tar.gz \
  output/checkpoint.json \
  output/gaussian_splat/ \
  output/logs/
```

---

## Emergency Procedures

### Force Stop Pipeline

```bash
# Find PID
ps aux | grep "gaspipe.cli run"

# Graceful stop (checkpoint saved)
kill -SIGTERM 

# Force kill (may corrupt checkpoint)
kill -9 
```

### Rollback to Previous Version

```bash
# Git rollback
git log --oneline
git checkout 

# Docker rollback
docker tag gaspipe:latest gaspipe:latest-backup
docker tag gaspipe: gaspipe:latest
```

---

## Quick Reference

### File Locations

```
output/
├── checkpoint.json          # Resume state
├── logs/<run_id>.log       # JSON logs
├── frames/                  # Step 1 output
├── cubemap_images/          # Step 2 output
├── realitycapture_output/   # Step 3 output
│   ├── sparse_points.ply
│   └── camera_poses.csv
└── gaussian_splat/          # Step 4 output (FINAL)
    └── *.psht
```

### Exit Codes

```
0: Success
1: General error
2: Configuration error
3: Validation error
4: Subprocess failure
5: Resume failure
```

### Important Commands

```bash
# Run
python -m gaspipe.cli run input.mp4 output/

# Resume
python -m gaspipe.cli resume output/

# Validate
python -m gaspipe.cli validate-config config.json

# Test
python -m gaspipe.cli self-test

# View logs
jq '.' output/logs/*.log

# Check status
jq '.current_step' output/checkpoint.json
```

---

**Last Updated**: 2025-09-29  
**Version**: 0.1.0  
**Maintainer**: TwiceOut Team