# /speckit.analyze Command Reference

Analyze speckit `tasks.md` for complexity scoring, dependency analysis, critical path, and delegation packaging.

## Synopsis

```
/speckit.analyze [TASKS_FILE] [OPTIONS]
```

## Description

The `/speckit.analyze` command performs comprehensive analysis of a speckit tasks.md file:

1. **Parses** tasks and dependencies (from `Dependencies:` fields and Mermaid graph)
2. **Scores** each task: complexity (1-10), estimated LOC, context tokens required
3. **Builds** dependency DAG and computes critical path
4. **Identifies** delegable tasks (complexity ≤ threshold, context ≤ threshold)
4. **Generates** minimal context packages for delegation to small LLMs
5. **Outputs** analysis artifacts and optional threshold sweep statistics

## Arguments

| Argument | Description |
|----------|-------------|
| `TASKS_FILE` | Path to tasks.md (default: current feature's `specs/###-feature/tasks.md`) |

## Options

| Option | Description |
|--------|-------------|
| `-o, --output DIR` | Output directory for analysis artifacts (default: `analysis/` alongside tasks.md) |
| `-t, --threshold STR` | Delegation thresholds as `complexity=X,context=Y` (default: `complexity=5,context=100000`) |
| `-c, --calibrate` | Calibrate scoring heuristics from `COMPLETED` tasks with actual implementations |
| `-e, --enrich` | Enrich the tasks.md file inline with score annotations |
| `-j, --json` | Output analysis JSON to stdout (for piping) |
| `-s, --sweep` | Perform full threshold sweep (precision/recall/F1 across all thresholds) |
| `--stats-history` | Update statistics history (CSV/Parquet) for trend tracking |
| `-v, --verbose` | Verbose output |

## Threshold Format

```
--threshold complexity=5,context=100000
```

- `complexity`: Maximum complexity score (1-10) for delegation
- `context`: Maximum context tokens for delegation

## Examples

### Basic Analysis

```bash
# Analyze current feature's tasks
/speckit.analyze

# Analyze specific tasks file
/speckit.analyze specs/003-ai-linux-iso/tasks.md
```

### With Calibration

```bash
# Calibrate from completed tasks (improves estimation accuracy)
/speckit.analyze --calibrate
```

### Custom Thresholds

```bash
# More conservative: only very simple tasks delegable
/speckit.analyze --threshold complexity=3,context=50000

# More aggressive: allow moderate complexity
/speckit.analyze --threshold complexity=7,context=150000
```

### Enrich Tasks File

```bash
# Add score annotations directly to tasks.md
/speckit.analyze --enrich
```

This adds after each task's header:
```markdown
**Score**: complexity=4, est_loc=180, context_tokens=42000, delegable=true
**ContextPackage**: analysis/delegation_package/T203/
```

And appends a delegation summary table at the end of the file.

### Full Threshold Sweep

```bash
# Analyze precision/recall/F1 across all threshold combinations
/speckit.analyze --sweep
```

Generates `threshold_analysis.md` with tables like:

| Complexity | Delegable | Precision | Recall | F1 |
|------------|-----------|-----------|--------|-----|
| 3 | 8 | 0.75 | 0.40 | 0.52 |
| 4 | 15 | 0.73 | 0.65 | 0.69 |
| **5** | **23** | **0.70** | **0.85** | **0.77** |
| 6 | 31 | 0.61 | 0.95 | 0.74 |

### Statistics History

```bash
# Append to stats_history.csv/parquet for cross-run analysis
/speckit.analyze --stats-history
```

### JSON Output (for automation)

```bash
# Pipe to jq or other tools
/speckit.analyze --json | jq '.delegation_summary.delegable'

# Save full result
/speckit.analyze --json > analysis_result.json
```

### Verbose Mode

```bash
/speckit.analyze -v
```

Shows detailed scoring breakdown for each task.

## Output Files

All outputs go to `OUTPUT_DIR` (default: `specs/###-feature/analysis/`):

| File | Description |
|------|-------------|
| `analysis.json` | Complete machine-readable result |
| `task_tree.md` | Visual tree with scores and critical path |
| `task_list.csv` | Spreadsheet-ready task list |
| `critical_path.md` | Critical path analysis + parallelization |
| `dependency_graph.mmd` | Mermaid graph (color-coded by score) |
| `dependency_graph_phases.mmd` | Mermaid grouped by phase |
| `threshold_analysis.md` | Threshold sweep report |
| `threshold_analysis.csv` | Threshold data for plotting |
| `stats_history.csv` | Historical stats (appended each run) |
| `stats_history.parquet` | Efficient Parquet for Pandas |
| `delegation_package/T###/context.md` | Minimal context for small LLM |

## Delegation Package Structure

For each delegable task (`delegable=true`):

```
delegation_package/T203/
├── context.md          # Task + criteria + interfaces + snippets + config + tests
├── interfaces.json     # Required upstream signatures
├── metadata.json       # Scores, deps, thresholds, etc.
├── refs/
│   ├── ref_1_trainer.py
│   └── ref_2_config.py
└── tests.md            # Expected test patterns
```

Total context typically **5k-50k tokens** — optimized for 4B models with 128k-256k context.

## Integration with speckit Workflow

```bash
# Standard workflow
/speckit.specify "Add feature"
/speckit.plan
/speckit.tasks

# NEW: Analyze for delegation
/speckit.analyze

# Review delegation candidates
cat specs/001-feature/analysis/task_tree.md

# Delegate T203 to small LLM
cat specs/001-feature/analysis/delegation_package/T203/context.md
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | File not found or parse error |
| 2 | Invalid arguments |
| 3 | Python package import error |

## See Also

- [speckit-analyzer README](../README.md)
- [Integration Guide](INTEGRATION_GUIDE.md)
- [Threshold Analysis](THRESHOLD_ANALYSIS.md)