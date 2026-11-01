# speckit-analyzer Integration Guide

Complete guide to integrating the speckit-analyzer extension into your speckit-based project.

## Prerequisites

- Existing speckit project with `.specify/` directory structure
- spec-kit v0.5.0+
- Python 3.10+ with pip
- Git repository (recommended)

## Installation

### Local Development Installation

```bash
# From your speckit project root
specify extension add /path/to/speckit-analyzer/specify-extension/speckit-analyzer --dev
```

This installs the extension into `.specify/extensions/speckit-analyzer/` with:
- Command: `speckit.speckit-analyzer.analyze`
- Bash wrapper: `.specify/extensions/speckit-analyzer/scripts/analyze-tasks.sh`
- Auto-hooks: `after_tasks` (auto-analyze, auto-enrich)
- Config: `.specify/extensions/speckit-analyzer/speckit-analyzer-config.yml`

### From GitHub (After Publishing)

```bash
specify extension add speckit-analyzer --from https://github.com/viking76/speckit-analyzer
```

### From Catalog (When Published)

```bash
specify extension add speckit-analyzer
```

## Configuration

### Project Config (`.specify/extensions/speckit-analyzer/speckit-analyzer-config.yml`)

Copy the template and customize:

```bash
cp .specify/extensions/speckit-analyzer/speckit-analyzer-config.template.yml \
   .specify/extensions/speckit-analyzer/speckit-analyzer-config.yml
```

```yaml
thresholds:
  complexity: 5          # Max complexity for delegation (1-10)
  context_tokens: 100000 # Max context tokens for delegation
  min_estimate_days: 0.5 # Skip micro-tasks

scoring:
  velocity_by_module:
    trainer: 120
    parser: 80
    ui: 100
    config: 150
  pattern_factors:
    implement: 1.0
    refactor: 1.5
    test: 0.6

context:
  max_snippets: 5
  max_snippet_lines: 50
  include_tests: true
  include_config: true

auto_analyze: false   # Run automatically after /speckit.tasks
auto_enrich: false    # Enrich tasks.md with scores
```

### Global Config (`.speckit-analyzer.yaml` at repo root)

```yaml
llm:
  base_url: "http://192.168.1.162:8889/v1"
  model: "qwen2.5-4b-instruct"
  timeout: 60
```

---

## Workflow Integration

### Standard speckit Workflow (Enhanced)

```bash
# 1. Create feature (unchanged)
/speckit.specify "Add user dashboard with metrics"

# 2. Create plan (unchanged)
/speckit.plan

# 3. Generate tasks (unchanged)
/speckit.tasks

# 4. NEW: Analyze for delegation (auto-prompted via hook)
/speckit.tasks  # → prompts: "Run automatic task analysis?"

# 5. Review results
cat specs/001-feature/analysis/task_tree.md
cat specs/001-feature/analysis/delegation_package/T###/context.md
```

### CI/CD Integration

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
      - name: Install extension
        run: |
          cd .specify/extensions/speckit-analyzer
          pip install -e . -q
      - name: Analyze tasks
        run: |
          for f in specs/*/tasks.md; do
            .specify/extensions/speckit-analyzer/scripts/analyze-tasks.sh "$f" --json
          done
      - name: Upload analysis artifacts
        uses: actions/upload-artifact@v4
        with:
          name: task-analysis
          path: specs/*/analysis/
```

### Auto-Analyze Hook

The extension registers an `after_tasks` hook that prompts after `/speckit.tasks`:

```
⚡ Run automatic task analysis for delegation packaging? [y/N]:
```

To auto-run without prompt, set in config:
```yaml
auto_analyze: true
```

### Auto-Enrich Hook

```yaml
auto_enrich: true
```

Enriches tasks.md with score annotations:
```markdown
### T203 Real-time Metrics Collection
**Score**: complexity=4, est_loc=180, context_tokens=42000, delegable=true
**ContextPackage**: analysis/delegation_package/T203/
```

---

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
metadata.json      # All scores, deps, thresholds
refs/              # 3-5 relevant code snippets from codebase
tests.md           # Expected test patterns
```

**Token budget**: Typically 5,000-50,000 tokens (well within 128k-256k limits).

---

## Calibration from Ground Truth

Improve estimation accuracy by calibrating from completed tasks:

```bash
# Requires tasks with:
# - status: COMPLETED
# - Implementation: path/to/actual/code.py
/speckit.speckit-analyzer.analyze --calibrate
```

This:
1. Reads actual implementations of `COMPLETED` tasks
2. Computes real LOC, cyclomatic complexity, context tokens
3. Fits velocity, pattern factors, keyword weights
4. Stores correlations (complexity vs actual LOC, etc.)
5. Applies learned weights to future scoring

**Minimum**: 5+ completed tasks with implementations for meaningful calibration.

---

## Threshold Tuning

### Finding Optimal Thresholds

```bash
# Full sweep with current data
/speckit.speckit-analyzer.analyze --sweep

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
python3 -c "
import pandas as pd
df = pd.read_parquet('analysis/stats_history.parquet')
print(df[['timestamp','delegable','threshold_complexity','threshold_context']].tail(10))
"
```

---

## Troubleshooting

### "Module not found: speckit_analyzer"

```bash
cd .specify/extensions/speckit-analyzer
pip install -e .
```

### "No tasks parsed"

Check tasks.md format — must have `### T### Task Title` headers with `**Phase**:`, `**Module**:`, `**Dependencies**:` fields.

### "No delegation packages created"

Verify thresholds aren't too strict:
```bash
/speckit.speckit-analyzer.analyze --threshold complexity=7,context=200000
```

### "Python package import error in CI"

Ensure PYTHONPATH includes the extension:
```yaml
env:
  PYTHONPATH: ".specify/extensions/speckit-analyzer:${PYTHONPATH}"
```

### Large context packages (> 100k tokens)

Reduce snippet count/lines:
```yaml
context:
  max_snippets: 3
  max_snippet_lines: 30
```

---

## Advanced Usage

### Custom Velocity by Module

```python
from speckit_analyzer.scoring import HeuristicScorer

scorer = HeuristicScorer(velocity_overrides={
    "my_custom_module": 200,
    "legacy_integration": 40,
})
```

### Extending Scoring Heuristics

```python
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
/speckit.speckit-analyzer.analyze --json | jq '.tasks[] | select(.delegable and .phase==2) | .id'

# Export delegation packages list
/speckit.speckit-analyzer.analyze --json | jq '.tasks[] | select(.delegable) | {id, package: .context_package_path}'
```

---

## Migration from Manual Analysis

1. Run `/speckit.speckit-analyzer.analyze --enrich` to add scores to existing tasks.md
2. Compare with your manual estimates
3. Adjust thresholds if needed
4. Use `--calibrate` to align heuristics with your project's reality

---

## Support

- Check `analysis/` outputs for debugging info
- Enable `-v` verbose flag for detailed scoring breakdown
- Review `stats_history.csv` for trend anomalies
- Open issues on the [speckit-analyzer repository](https://github.com/viking76/speckit-analyzer)