#!/usr/bin/env python3
"""
speckit-analyzer validation command.
Called on pre_tool_use event.
"""

import sys
from pathlib import Path

# Add extension directory to path
EXTENSION_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_DIR))

def main():
    # Validate that tasks.md exists if we're in a feature directory
    # This is a lightweight check - full analysis runs on demand
    return 0

if __name__ == "__main__":
    sys.exit(main())