# GaSPipe 🎥 → 🧊 → 🎯

**Automated 360° Video to Gaussian Splats Pipeline**

[![CI Status](https://github.com/yourusername/gaspipe/workflows/GaSPipe%20CI/badge.svg)](https://github.com/yourusername/gaspipe/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Transform 360° equirectangular videos into high-quality Gaussian Splat 3D models through a fully automated, resumable pipeline.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- FFmpeg with `v360` filter
- RealityCapture CLI
- PostShot CLI

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/gaspipe.git
cd gaspipe

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .

# Verify installation
python -m gaspipe.cli self-test
```

### Basic Usage

```bash
# Process a 360° video
python -m gaspipe.cli run input_360.mp4 output/ --config config.json

# Resume interrupted pipeline
python -m gaspipe.cli resume output/

# Check configuration
python -m gaspipe.cli validate-config config.json
```

---

## 📐 Pipeline Overview

```
┌─────────────────────┐
│  360° Video (MP4)   │
└──────────┬──────────┘
           │ FFmpeg
           │ Extract frames at 1-10 FPS
           ↓
┌─────────────────────┐
│   Frames (PNG/JPG)  │
└──────────┬──────────┘
           │ FFmpeg v360
           │ Generate 9-direction cubemap
           ↓
┌─────────────────────┐
│  Cubemap Images     │
│  (front, back, etc) │
└──────────┬──────────┘
           │ RealityCapture
           │ Camera pose estimation
           ↓
┌─────────────────────┐
│   Camera Poses +    │
│   Sparse 3D Cloud   │
└──────────┬──────────┘
           │ PostShot
           │ Gaussian Splat training
           ↓
┌─────────────────────┐
│  Gaussian Splat 3D  │
│     (.psht file)    │
└─────────────────────┘
```

**Key Features**:
- ✅ **Resumable**: Interrupted pipelines resume from last checkpoint
- ✅ **Robust**: Automatic retry with exponential backoff
- ✅ **Observable**: JSON structured logging with full traceability
- ✅ **Validated**: SHA256 checksums ensure output integrity
- ✅ **Configurable**: JSON-based configuration

---

## ⚙️ Configuration

Create a `config.json` file:

```json
{
  "ffmpeg_path": "ffmpeg",
  "rc_path": "/path/to/RealityCapture",
  "postshot_path": "/path/to/postshot-cli",
  "rc_settings_path": "/path/to/RC_Settings",
  "video": {
    "fps": 2.0,
    "resolution": "4K",
    "format": "PNG",
    "quality": "high"
  },
  "cubemap": {
    "size": "1920x1920",
    "format": "PNG",
    "quality": "high"
  },
  "postshot": {
    "profile": "Splat MCMC",
    "steps": 25
  },
  "processing": {
    "timeout_minutes": 30
  }
}
```

---

## 🛠️ CLI Commands

### `run` - Execute Full Pipeline

```bash
python -m gaspipe.cli run VIDEO OUTPUT [OPTIONS]

Arguments:
  VIDEO                  Input 360° video file
  OUTPUT                 Output directory

Options:
  --config PATH          Configuration file
  --run-id UUID          Custom run ID
  --log-level LEVEL      DEBUG, INFO, WARNING, ERROR

Example:
  python -m gaspipe.cli run video360.mp4 output_dir/ \
    --config config.json \
    --log-level DEBUG
```

### `resume` - Resume from Checkpoint

```bash
python -m gaspipe.cli resume OUTPUT

Example:
  python -m gaspipe.cli resume output_dir/
```

### `validate-config` - Validate Configuration

```bash
python -m gaspipe.cli validate-config CONFIG

Example:
  python -m gaspipe.cli validate-config config.json
```

### `self-test` - Test Dependencies

```bash
python -m gaspipe.cli self-test [OPTIONS]

Options:
  --rc-path PATH         RealityCapture binary
  --postshot-path PATH   PostShot CLI binary

Example:
  python -m gaspipe.cli self-test \
    --rc-path=/usr/local/bin/RealityCapture
```

---

## 📊 Output Structure

```
output_dir/
├── checkpoint.json              # Resume state
├── logs/
│   └── <run_id>.log            # JSON logs
├── frames/
│   ├── frame_000001.png
│   ├── frame_000001.png.ok
│   └── frame_000001.png.sha256
├── cubemap_images/
│   ├── frame_000001_front.png
│   └── ...
├── realitycapture_output/
│   ├── sparse_points.ply
│   ├── camera_poses.csv
│   └── project.rcproj
└── gaussian_splat/
    └── video360.psht
```

---

## 🔍 Monitoring & Debugging

### View Logs

```bash
# Watch log file
tail -f output/logs/.log | jq

# Filter errors
jq 'select(.level=="ERROR")' output/logs/*.log
```

### Check Progress

```bash
# Current step
jq '.current_step' output/checkpoint.json

# Failed steps
jq '.manifest[] | select(.status=="failed")' output/checkpoint.json
```

---

## 🐳 Docker Support

```bash
# Build image
docker build -t gaspipe:latest .

# Run pipeline
docker run --rm \
  -v $(pwd)/input:/data/input \
  -v $(pwd)/output:/data/output \
  gaspipe:latest run /data/input/video.mp4 /data/output
```

---

## 🧪 Development

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/gaspipe --cov-report=html
```

---

## 📈 Performance Tips

- Lower FPS (1-2) for faster processing
- Use JPG for 50% smaller files
- Match resolution to use case (4K sufficient for most)
- Start with 10-15k steps for prototyping
- Use 25-30k steps for production quality

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- **FFmpeg** for video processing
- **RealityCapture** for camera pose estimation
- **PostShot** for Gaussian Splatting
- **Pydantic** for type safety

---

**Made with ❤️ by TwiceOut Team**