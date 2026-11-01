#!/usr/bin/env python3
"""
speckit-analyzer extension initialization command.
Called on session_start event.
"""

import sys
from pathlib import Path

# Add extension directory to path
EXTENSION_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_DIR))

from speckit_analyzer import __version__

def main():
    print(f"speckit-analyzer v{__version__} initialized")
    print("Ready for task analysis and delegation packaging")
    return 0

if __name__ == "__main__":
    sys.exit(main())