#!/usr/bin/env python3
"""
Atomic file operations and integrity helpers.
"""
import hashlib
import tempfile
from pathlib import Path
from typing import Union, Optional


def get_marker_path(file_path: Path, marker_type: str) -> Path:
    """
    Get the path for marker files (.ok, .sha256) in separate .markers directory.
    
    Args:
        file_path: Original file path
        marker_type: Type of marker ('ok' or 'sha256')
    
    Returns:
        Path to marker file in .markers directory
    """
    # Find the output root directory
    parts = file_path.parts
    output_idx = None
    
    # Look for directory that contains 'output' in the path
    for i, part in enumerate(parts):
        if 'output' in part:
            output_idx = i
            break
    
    if output_idx is None:
        # Fallback: use parent directory
        output_root = file_path.parent.parent
    else:
        output_root = Path(*parts[:output_idx+1])
    
    # Build relative path from output root
    try:
        relative_path = file_path.relative_to(output_root)
    except ValueError:
        # If file is not relative to output_root, use just filename
        relative_path = Path(file_path.parent.name) / file_path.name
    
    # Create marker directory structure
    marker_dir = output_root / '.markers' / relative_path.parent
    marker_dir.mkdir(parents=True, exist_ok=True)
    
    return marker_dir / f"{file_path.name}.{marker_type}"


def atomic_write(path: Path, data: Union[str, bytes], mode: str = 'w') -> None:
    """
    Write file atomically using temp file + rename.
    
    Args:
        path: Target file path
        data: Content to write
        mode: File mode ('w' for text, 'wb' for binary)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file in same directory (ensures same filesystem)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        if 'b' in mode:
            with open(temp_fd, 'wb') as f:
                f.write(data)  # type: ignore
        else:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                f.write(data)  # type: ignore
        
        # Atomic rename
        Path(temp_path).replace(path)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def write_ok_and_sha(file_path: Path) -> tuple[Path, Path]:
    """
    Create .ok marker and .sha256 checksum file in .markers directory.
    
    Returns:
        Tuple of (ok_path, sha_path)
    """
    ok_path = get_marker_path(file_path, 'ok')
    sha_path = get_marker_path(file_path, 'sha256')
    
    # Compute and write SHA256
    checksum = compute_sha256(file_path)
    atomic_write(sha_path, checksum, mode='w')
    
    # Write .ok marker (empty file)
    atomic_write(ok_path, '', mode='w')
    
    return ok_path, sha_path


def verify_file_integrity(file_path: Path) -> bool:
    """
    Verify file integrity using .sha256 checksum from .markers directory.
    
    Returns:
        True if checksum matches, False otherwise
    """
    sha_path = get_marker_path(file_path, 'sha256')
    
    if not sha_path.exists():
        return False
    
    try:
        expected_checksum = sha_path.read_text().strip()
        actual_checksum = compute_sha256(file_path)
        
        return expected_checksum == actual_checksum
    except Exception:
        return False


def is_completed(file_path: Path) -> bool:
    """Check if file has .ok marker and valid checksum in .markers directory."""
    ok_path = get_marker_path(file_path, 'ok')
    
    if not ok_path.exists():
        return False
    
    return verify_file_integrity(file_path)


def cleanup_markers(file_path: Path) -> None:
    """
    Remove marker files for a given file.
    Useful when you want to force regeneration.
    
    Args:
        file_path: Original file path whose markers to remove
    """
    ok_path = get_marker_path(file_path, 'ok')
    sha_path = get_marker_path(file_path, 'sha256')
    
    ok_path.unlink(missing_ok=True)
    sha_path.unlink(missing_ok=True)


def list_completed_files(directory: Path, pattern: str = "*") -> list[Path]:
    """
    List all files in directory that have been completed (have .ok markers).
    
    Args:
        directory: Directory to scan
        pattern: Glob pattern for files (default: "*")
    
    Returns:
        List of completed file paths
    """
    completed = []
    for file_path in directory.glob(pattern):
        if file_path.is_file() and is_completed(file_path):
            completed.append(file_path)
    return completed