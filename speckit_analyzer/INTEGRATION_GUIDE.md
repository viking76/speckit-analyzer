# speckit-analyzer Integration Guide

Complete guide to integrating the speckit-analyzer extension into your speckit-based project.

## Prerequisites

- Existing speckit project with `.specify/` directory structure
- Python 3.10+ with pip
- Git repository (recommended)

## Installation

### Option 1: Automated Integration (Recommended)

```bash
cd /path/to/your/speckit/project
./.specify/scripts/bash/integrate-analyze.sh
```

This script:
1. Verifies the analyzer package exists
2. Creates `/speckit.analyze` command wrapper
3. Updates `tasks-template.md` with Score/Delegation section
4. Creates `analysis-template.md`
5. Installs Python package in development mode

### Option 2: Manual Integration

If you prefer manual control:

```bash
# 1. Ensure analyzer package is available
cd .specify/python/speckit_analyzer
pip install -e . --break-system-packages

# 2. Make analyze-tasks.sh executable
chmod +x .specify/scripts/bash/analyze-tasks.sh

# 3. Create command wrapper
cat > .specify/scripts/bash/speckit-analyze << 'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
eval $(get_feature_paths)
TASKS_FILE="${1:-$IMPL_TASKS}"
shift || true
OUTPUT_DIR="${IMPL_TASKS%/*}/analysis"
PYTHONPATH="${SPECIFY_DIR}/python:$PYTHONPATH" python3 -m speckit_analyzer.cli analyze "$TASKS_FILE" --output "$OUTPUT_DIR" "$@"
EOF
chmod +x .specify/scripts/bash/speckit-analyze

# 4. Update tasks-template.md (add Score/Delegation section)
# See TEMPLATE_UPDATE.md for the exact content to append
```

## Configuration

### Project-Level Config (`.speckit-analyzer.yaml`)

Create at repository root:

```yaml
# .speckit-analyzer.yaml
llm:
  base_url: "http://192.168.1.162:8889/v1"  # Unsloth endpoint
  model: "qwen2.5-4b-instruct"
  timeout: 60
  max_retries: 3

thresholds:
  complexity: 5          # Max complexity for delegation (1-10)
  context_tokens: 100000 # Max context tokens for delegation
  min_estimate_days: 0.5 # Skip micro-tasks

scoring:
  # Override default velocities (LOC/day per module)
  velocity_by_module:
    trainer: 120
    model_manager: 100
    parser: 80
    ui: 100
    config: 150
    # Add your module types

  # Pattern factors for LOC estimation
  pattern_factors:
    implement: 1.0
    create: 1.0
    refactor: 1.5
    optimize: 1.3
    test: 0.6
    document: 0.3

context:
  max_snippets: 5
  max_snippet_lines: 50
  include_tests: true
  include_config: true

retry_tracking:
  enabled: true
  compaction_threshold: 0.15
  persist_path: "analysis/retry_stats.json"
```

### Per-Run Override

```bash
/speckit.analyze --threshold complexity=4,context=80000
```

## Workflow Integration

### Standard speckit Workflow (Enhanced)

```bash
# 1. Create feature (unchanged)
/speckit.specify "Add user dashboard with metrics"

# 2. Create plan (unchanged)
/speckit.plan

# 3. Generate tasks (unchanged)
/speckit.tasks

# 4. NEW: Analyze for delegation
/speckit.analyze

# 5. Review results
cat specs/001-feature/analysis/task_tree.md
cat specs/001-feature/analysis/delegation_package/T###/context.md
```

### CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/analyze.yml
name: Task Analysis
on:
  push:
    paths:
      - 'specs/**/tasks.md'
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install analyzer
        run: |
          cd .specify/python/speckit_analyzer
          pip install -e . -q
      - name: Analyze tasks
        run: |
          for f in specs/*/tasks.md; do
            PYTHONPATH=.specify/python:$PYTHONPATH python3 -m speckit_analyzer.cli analyze "$f" --output "${f%/*}/analysis" --json
          done
      - name: Upload analysis artifacts
        uses: actions/upload-artifact@v4
        with:
          name: task-analysis
          path: specs/*/analysis/
```

### Auto-Analyze Hook

Create `.specify/hooks/post-tasks-generation/analyze.sh`:

```bash
#!/usr/bin/env bash
# Auto-analyze after /speckit.tasks completes

set -euo pipefail

SPECIFY_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$SPECIFY_DIR/.specify/scripts/bash/common.sh"

eval $(get_feature_paths)

if [[ -f "$IMPL_TASKS" ]]; then
    echo "[speckit-analyze] Auto-analyzing $IMPL_TASKS..."
    PYTHONPATH="$SPECIFY_DIR/.specify/python:$PYTHONPATH" \
    python3 -m speckit_analyzer.cli analyze "$IMPL_TASKS" --output "${IMPL_TASKS%/*}/analysis" --enrich
fi
```

Make executable:
```bash
chmod +x .specify/hooks/post-tasks-generation/analyze.sh
```

## Understanding Outputs

### For Human Review

| File | When to Use |
|------|-------------|
| `task_tree.md` | Quick overview of all tasks with scores |
| `critical_path.md` | Scheduling and bottleneck identification |
| `threshold_analysis.md` | Tuning delegation thresholds |
| `delegation_package/T###/context.md` | Handoff to small LLM |

### For Automation

| File | Use Case |
|------|----------|
| `analysis.json` | Full programmatic access |
| `task_list.csv` | Spreadsheet/BI tool import |
| `stats_history.parquet` | Pandas trend analysis |
| `threshold_analysis.csv` | Threshold optimization plots |

### Delegation Package Contents

Each `delegation_package/T###/` contains:

```
context.md         # Complete minimal context (copy-paste to small LLM)
interfaces.json    # Required upstream function/class signatures
metadata.json      # All scores, thresholds, dependencies
refs/              # 3-5 relevant code snippets from codebase
tests.md           # Expected test patterns
```

**Token budget**: Typically 5,000-50,000 tokens (well within 128k-256k limits).

## Calibration from Ground Truth

Improve estimation accuracy by calibrating from completed tasks:

```bash
# Requires tasks with:
# - status: COMPLETED
# - Implementation: path/to/actual/code.py
/speckit.analyze --calibrate
```

This:
1. Reads actual implementations of `COMPLETED` tasks
2. Computes real LOC, cyclomatic complexity, context tokens
3. Fits velocity, pattern factors, keyword weights
4. Stores correlations (complexity vs actual LOC, etc.)
5. Applies learned weights to future scoring

**Minimum**: 5+ completed tasks with implementations for meaningful calibration.

## Threshold Tuning

### Finding Optimal Thresholds

```bash
# Full sweep with current data
/speckit.analyze --sweep

# Check results
cat analysis/threshold_analysis.md
```

Key metrics:
- **Precision**: Of delegated tasks, how many were actually simple?
- **Recall**: Of actually simple tasks, how many were delegated?
- **F1**: Harmonic mean — balance of precision/recall

### Recommended Starting Points

| Project Type | Complexity | Context | Rationale |
|--------------|------------|---------|-----------|
| Conservative | 4 | 50,000 | High precision, low false positives |
| **Balanced** | **5** | **100,000** | **Good F1, reasonable delegation rate** |
| Aggressive | 6 | 150,000 | High recall, more delegation |

### Monitoring Threshold Effectiveness

Track in `stats_history.csv`:
```bash
# After multiple runs
python3 -c "
import pandas as pd
df = pd.read_parquet('analysis/stats_history.parquet')
print(df[['timestamp','delegable','threshold_complexity','threshold_context']].tail(10))
"
```

## Troubleshooting

### "Module not found: speckit_analyzer"

```bash
cd .specify/python/speckit_analyzer
pip install -e . --break-system-packages
```

### "No tasks parsed"

Check tasks.md format — must have `### T### Task Title` headers with `**Phase**:`, `**Module**:`, `**Dependencies**:` fields.

### "No delegation packages created"

Verify thresholds aren't too strict:
```bash
/speckit.analyze --threshold complexity=7,context=200000
```

### "Python package import error in CI"

Ensure PYTHONPATH includes the analyzer:
```yaml
env:
  PYTHONPATH: ".specify/python:${PYTHONPATH}"
```

### Large context packages (> 100k tokens)

Reduce snippet count/lines:
```yaml
# .speckit-analyzer.yaml
context:
  max_snippets: 3
  max_snippet_lines: 30
```

## Advanced Usage

### Custom Velocity by Module

If your project has unique module types:

```python
# In a custom script
from speckit_analyzer.scoring import HeuristicScorer

scorer = HeuristicScorer(velocity_overrides={
    "my_custom_module": 200,  # Very fast module
    "legacy_integration": 40,  # Slow, complex module
})
```

### Extending Scoring Heuristics

Add domain-specific complexity keywords:

```python
# In a custom script
from speckit_analyzer.scoring.heuristics import HeuristicScorer

scorer = HeuristicScorer()
scorer.COMPLEXITY_KEYWORDS.update({
    "kubernetes": 2,
    "distributed": 3,
    "real-time": 2,
    "gpu": 1,
})
```

### Post-Processing Analysis JSON

```bash
# Find all delegable tasks in Phase 2
/speckit.analyze --json | jq '.tasks[] | select(.delegable and .phase==2) | .id'

# Export delegation packages list
/speckit.analyze --json | jq '.tasks[] | select(.delegable) | {id, package: .context_package_path}'
```

## Migration from Manual Analysis

If you previously analyzed tasks manually:

1. Run `/speckit.analyze --enrich` to add scores to existing tasks.md
2. Compare with your manual estimates
3. Adjust thresholds if needed
4. Use `--calibrate` to align heuristics with your project's reality

## Support

- Check `analysis/` outputs for debugging info
- Enable `-v` verbose flag for detailed scoring breakdown
- Review `stats_history.csv` for trend anomalies
- Open issues on the speckit repository

## Version Compatibility

| speckit-analyzer | speckit | Python |
|------------------|---------|--------|
| 0.1.x | Any with `.specify/` | 3.10+ |

---

*Part of the speckit ecosystem — Apache-2.0 licensed*