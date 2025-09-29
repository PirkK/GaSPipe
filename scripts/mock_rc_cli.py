#!/usr/bin/env python3
"""Mock RealityCapture CLI for testing."""
import sys
import csv
from pathlib import Path

def main():
    """Mock RealityCapture CLI - simula output per test."""
    args = sys.argv[1:]
    
    # Parse arguments
    output_ply = None
    output_csv = None
    
    i = 0
    while i < len(args):
        if args[i] == '-exportSparsePointCloud':
            output_ply = Path(args[i + 1])
            i += 2
        elif args[i] == '-exportRegistration':
            output_csv = Path(args[i + 1])
            i += 2
        else:
            i += 1
    
    # Create mock outputs
    if output_ply:
        output_ply.parent.mkdir(parents=True, exist_ok=True)
        output_ply.write_text("MOCK_PLY_DATA\n" * 100)  # Mock point cloud
    
    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['image_name', 'pos_x', 'pos_y', 'pos_z',
                           'r00', 'r01', 'r02', 'r10', 'r11', 'r12', 'r20', 'r21', 'r22', 'focal'])
            # Mock multiple camera poses
            for i in range(10):
                writer.writerow([f'img_{i:03d}.png', str(i*0.1), '0.0', '1.8',
                               '1.0', '0.0', '0.0', '0.0', '1.0', '0.0', '0.0', '0.0', '1.0', '50.0'])
    
    return 0

if __name__ == '__main__':
    sys.exit(main())