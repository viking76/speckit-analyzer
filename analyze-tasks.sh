#!/usr/bin/env bash
# speckit-analyze wrapper script
# Called by /speckit.analyze command

set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get repo root
REPO_ROOT=$(get_repo_root)
SPECIFY_DIR="$REPO_ROOT/.specify"

# If first arg is a file path, use it directly
if [[ -n "${1:-}" && -f "$1" ]]; then
    TASKS_FILE="$1"
    shift
else
    # Try to get feature paths (works when on a feature branch)
    if eval $(get_feature_paths 2>/dev/null) && [[ -n "${IMPL_TASKS:-}" ]]; then
        TASKS_FILE="$IMPL_TASKS"
    else
        echo "Error: No tasks file specified." >&2
        echo "Usage: $0 [TASKS_FILE] [OPTIONS]" >&2
        echo "  TASKS_FILE  Path to tasks.md" >&2
        exit 1
    fi
fi

# Default output directory
OUTPUT_DIR="${TASKS_FILE%/*}/analysis"

# Pass all remaining args to Python
PYTHONPATH="${SPECIFY_DIR}/python:${PYTHONPATH:-}" python3 -m speckit_analyzer.cli analyze "$TASKS_FILE" --output "$OUTPUT_DIR" "$@"