#!/usr/bin/env python3
"""
speckit-analyzer Python entry point for spec-kit extension.
Can be called directly or via the bash wrapper.
"""

import sys
from pathlib import Path

# Add extension directory to path
EXTENSION_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_DIR))

from speckit_analyzer.cli import app

if __name__ == "__main__":
    app()