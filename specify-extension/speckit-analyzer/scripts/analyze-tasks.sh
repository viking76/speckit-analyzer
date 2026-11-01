#!/usr/bin/env bash
# speckit-analyzer task analysis script
# Part of speckit-analyzer extension

set -euo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_DIR="$(dirname "$SCRIPT_DIR")"
SPECIFY_DIR="${EXTENSION_DIR}/../.."

# Source spec-kit common functions if available
if [[ -f "${SPECIFY_DIR}/scripts/bash/common.sh" ]]; then
    source "${SPECIFY_DIR}/scripts/bash/common.sh"
fi

# Get repo root
get_repo_root() {
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
    else
        local script_dir="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        (cd "$script_dir/../../.." && pwd)
    fi
}

REPO_ROOT=$(get_repo_root)
SPECIFY_DIR="${REPO_ROOT}/.specify"

# If first arg is a file path, use it directly
if [[ -n "${1:-}" && -f "$1" ]]; then
    TASKS_FILE="$1"
    shift
else
    # Try to get feature paths
    DEFAULT_TASKS=""
    DEFAULT_OUTPUT=""
    if eval $(get_feature_paths 2>/dev/null); then
        DEFAULT_TASKS="${IMPL_TASKS:-}"
        DEFAULT_OUTPUT="${IMPL_TASKS%/*}/analysis"
    fi

    TASKS_FILE="${1:-$DEFAULT_TASKS}"
    shift || true

    if [[ -z "$TASKS_FILE" ]]; then
        echo "Error: No tasks file specified." >&2
        echo "Usage: $0 [TASKS_FILE] [OPTIONS]" >&2
        echo "  TASKS_FILE  Path to tasks.md" >&2
        exit 1
    fi
fi

# Default output directory
OUTPUT_DIR="${TASKS_FILE%/*}/analysis"

# Pass all remaining args to Python
PYTHONPATH="${EXTENSION_DIR}:${PYTHONPATH:-}" python3 -m speckit_analyzer.cli analyze "$TASKS_FILE" --output "$OUTPUT_DIR" "$@"