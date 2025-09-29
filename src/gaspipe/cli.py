#!/usr/bin/env python3
"""
GaSPipe CLI with run, resume, validate-config, self-test commands.

Exit Codes:
    0: Success
    1: General error
    2: Configuration error
    3: Validation error
    4: Subprocess failure
    5: Resume failure
"""
import argparse
import logging
import sys
import uuid
from pathlib import Path

from .logging_config import setup_logging
from .validate import validate_checkpoint, GaSPipeValidationError

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_VALIDATION_ERROR = 3
EXIT_SUBPROCESS_ERROR = 4
EXIT_RESUME_ERROR = 5


def cmd_run(args: argparse.Namespace) -> int:
    """Execute full pipeline run."""
    run_id = args.run_id or str(uuid.uuid4())
    
    setup_logging(
        log_level=args.log_level,
        log_file=args.output / 'logs' / f'{run_id}.log' if args.output else None,
        run_id=run_id
    )
    
    logger.info(f"Starting GaSPipe run", extra={
        "run_id": run_id,
        "meta": {
            "video": str(args.video),
            "output": str(args.output),
            "config": str(args.config)
        }
    })
    
    try:
        # Import here to avoid circular dependencies
        from .pipeline import run_pipeline
        
        run_pipeline(
            video_file=args.video,
            output_dir=args.output,
            config_file=args.config,
            run_id=run_id
        )
        
        logger.info("Pipeline completed successfully", extra={"run_id": run_id})
        return EXIT_SUCCESS
        
    except GaSPipeValidationError as e:
        logger.error(f"Validation error: {e.error.message}", extra={
            "run_id": run_id,
            "meta": e.to_dict()
        })
        return EXIT_VALIDATION_ERROR
        
    except Exception as e:
        logger.exception("Pipeline failed", extra={"run_id": run_id})
        return EXIT_ERROR


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume pipeline from checkpoint."""
    checkpoint_path = args.output / 'checkpoint.json'
    
    try:
        checkpoint = validate_checkpoint(checkpoint_path)
    except GaSPipeValidationError as e:
        logger.error(f"Invalid checkpoint: {e.error.message}")
        return EXIT_RESUME_ERROR
    
    run_id = checkpoint.run_id
    setup_logging(
        log_level=args.log_level,
        log_file=args.output / 'logs' / f'{run_id}_resume.log',
        run_id=run_id
    )
    
    logger.info(f"Resuming pipeline from {checkpoint.current_step}", extra={
        "run_id": run_id,
        "meta": {"checkpoint": str(checkpoint_path)}
    })
    
    try:
        from .pipeline import resume_pipeline
        
        resume_pipeline(checkpoint=checkpoint)
        
        logger.info("Pipeline resumed and completed", extra={"run_id": run_id})
        return EXIT_SUCCESS
        
    except Exception as e:
        logger.exception("Resume failed", extra={"run_id": run_id})
        return EXIT_RESUME_ERROR


def cmd_validate_config(args: argparse.Namespace) -> int:
    """Validate configuration file."""
    try:
        from .config import load_config
        
        config = load_config(args.config)
        print(f"✓ Configuration valid: {args.config}")
        print(f"  FFmpeg: {config.get('ffmpeg_path', 'NOT SET')}")
        print(f"  RealityCapture: {config.get('rc_path', 'NOT SET')}")
        print(f"  PostShot: {config.get('postshot_path', 'NOT SET')}")
        
        return EXIT_SUCCESS
        
    except Exception as e:
        print(f"✗ Configuration invalid: {e}")
        return EXIT_CONFIG_ERROR


def cmd_self_test(args: argparse.Namespace) -> int:
    """Test external dependencies (FFmpeg, RC, PostShot)."""
    from .subprocess_wrapper import run_subprocess, SubprocessError
    
    print("Testing GaSPipe dependencies...\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test FFmpeg
    try:
        output = run_subprocess(['ffmpeg', '-version'], timeout=10)
        version = output.split('\n')[0]
        print(f"✓ FFmpeg: {version}")
        tests_passed += 1
    except (SubprocessError, FileNotFoundError) as e:
        print(f"✗ FFmpeg: Not found or failed ({e})")
        tests_failed += 1
    
    # Test RealityCapture (if path provided)
    rc_path = args.rc_path or 'RealityCapture'
    try:
        run_subprocess([rc_path, '-help'], timeout=10)
        print(f"✓ RealityCapture: Available at {rc_path}")
        tests_passed += 1
    except (SubprocessError, FileNotFoundError):
        print(f"✗ RealityCapture: Not found at {rc_path}")
        tests_failed += 1
    
    # Test PostShot (if path provided)
    ps_path = args.postshot_path or 'postshot-cli'
    try:
        run_subprocess([ps_path, '--help'], timeout=10)
        print(f"✓ PostShot: Available at {ps_path}")
        tests_passed += 1
    except (SubprocessError, FileNotFoundError):
        print(f"✗ PostShot: Not found at {ps_path}")
        tests_failed += 1
    
    print(f"\nResults: {tests_passed} passed, {tests_failed} failed")
    return EXIT_SUCCESS if tests_failed == 0 else EXIT_ERROR


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GaSPipe: 360° Video → Gaussian Splats Pipeline"
    )
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # run command
    run_parser = subparsers.add_parser('run', help='Execute full pipeline')
    run_parser.add_argument('video', type=Path, help='Input 360° video file')
    run_parser.add_argument('output', type=Path, help='Output directory')
    run_parser.add_argument('--config', type=Path, help='Configuration file')
    run_parser.add_argument('--run-id', help='UUID for run tracking')
    run_parser.set_defaults(func=cmd_run)
    
    # resume command
    resume_parser = subparsers.add_parser('resume', help='Resume from checkpoint')
    resume_parser.add_argument('output', type=Path, help='Output directory with checkpoint')
    resume_parser.set_defaults(func=cmd_resume)
    
    # validate-config command
    validate_parser = subparsers.add_parser('validate-config', help='Validate configuration')
    validate_parser.add_argument('config', type=Path, help='Configuration file')
    validate_parser.set_defaults(func=cmd_validate_config)
    
    # self-test command
    test_parser = subparsers.add_parser('self-test', help='Test dependencies')
    test_parser.add_argument('--rc-path', help='RealityCapture binary path')
    test_parser.add_argument('--postshot-path', help='PostShot CLI path')
    test_parser.set_defaults(func=cmd_self_test)
    
    args = parser.parse_args()
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return EXIT_ERROR
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == '__main__':
    sys.exit(main())