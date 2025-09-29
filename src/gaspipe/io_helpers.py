#!/usr/bin/env python3
"""
Atomic file operations and integrity helpers.
"""
import hashlib
import tempfile
from pathlib import Path
from typing import Union


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
    Create .ok marker and .sha256 checksum file.
    
    Returns:
        Tuple of (ok_path, sha_path)
    """
    ok_path = file_path.with_suffix(file_path.suffix + '.ok')
    sha_path = file_path.with_suffix(file_path.suffix + '.sha256')
    
    # Compute and write SHA256
    checksum = compute_sha256(file_path)
    atomic_write(sha_path, checksum, mode='w')
    
    # Write .ok marker (empty file)
    atomic_write(ok_path, '', mode='w')
    
    return ok_path, sha_path


def verify_file_integrity(file_path: Path) -> bool:
    """
    Verify file integrity using .sha256 checksum.
    
    Returns:
        True if checksum matches, False otherwise
    """
    sha_path = file_path.with_suffix(file_path.suffix + '.sha256')
    
    if not sha_path.exists():
        return False
    
    expected_checksum = sha_path.read_text().strip()
    actual_checksum = compute_sha256(file_path)
    
    return expected_checksum == actual_checksum


def is_completed(file_path: Path) -> bool:
    """Check if file has .ok marker and valid checksum."""
    ok_path = file_path.with_suffix(file_path.suffix + '.ok')
    
    if not ok_path.exists():
        return False
    
    return verify_file_integrity(file_path)