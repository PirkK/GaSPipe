#!/usr/bin/env python3
"""Mock PostShot CLI for testing."""
import sys
from pathlib import Path

def main():
    args = sys.argv[1:]
    
    # Parse --output argument
    output_file = None
    i = 0
    while i < len(args):
        if args[i] == '--output':
            output_file = Path(args[i + 1])
            i += 2
        else:
            i += 1
    
    # Create mock .psht file
    if output_file:
        output_file.write_text("MOCK_POSTSHOT_PROJECT")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())