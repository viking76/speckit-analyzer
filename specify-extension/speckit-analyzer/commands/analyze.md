---
command: speckit.analyzer.analyze
description: "Analyze tasks.md for complexity scoring, dependency analysis, critical path, and delegation packaging"
---

# /speckit.analyze

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
5. **Generates** minimal context packages for delegation to small LLMs
6. **Outputs** analysis artifacts and optional threshold sweep statistics

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
# Current feature (auto-detect on feature branch)
/speckit.analyze

# Specific tasks file
/speckit.analyze specs/003-ai-linux-iso/tasks.md
```

### With Calibration

```bash
# Calibrate from completed tasks (improves estimation accuracy)
/speckit.analyze --calibrate
```

### Custom Thresholds

```bash
# Conservative: only very simple tasks delegable
/speckit.analyze --threshold complexity=3,context=50000

# Aggressive: allow moderate complexity
/speckit.analyze --threshold complexity=7,context=150000
```

### Enrich Tasks File

```bash
# Add score annotations directly to tasks.md
/speckit.analyze --enrich
```

### Full Threshold Sweep

```bash
# Precision/recall/F1 across all threshold combinations
/speckit.analyze --sweep
```

### JSON Output (Automation)

```bash
# Pipe to jq or other tools
/speckit.analyze --json | jq '.delegation_summary.delegable'

# Save full result
/speckit.analyze --json > analysis_result.json
```

## Outputs

All artifacts in `specs/###-feature/analysis/`:

| File | Description |
|------|-------------|
| `analysis.json` | Complete machine-readable result |
| `task_tree.md` | Visual tree with scores + critical path |
| `task_list.csv` | Spreadsheet-ready task list |
| `critical_path.md` | Critical path + parallelization |
| `dependency_graph.mmd` | Mermaid graph (color-coded by score) |
| `dependency_graph_phases.mmd` | Mermaid grouped by phase |
| `threshold_analysis.md` | Threshold sweep report |
| `threshold_analysis.csv` | Threshold data for plotting |
| `stats_history.csv` | Historical stats across runs |
| `stats_history.parquet` | Efficient Parquet for Pandas |
| `delegation_package/T###/context.md` | Minimal context for delegation |

## Delegation Package Example

Each delegable task gets a `delegation_package/T###/` containing:

- `context.md` — Task + criteria + interfaces + snippets + config + tests
- `interfaces.json` — Required upstream signatures
- `metadata.json` — Scores, deps, thresholds
- `refs/` — 3-5 relevant code snippets from codebase
- `tests.md` — Expected test patterns

Total context typically **5k-50k tokens** — optimized for 4B models with 128k-256k context.

## Configuration

Create `.speckit-analyzer.yaml` at repo root:

```yaml
thresholds:
  complexity: 5
  context_tokens: 100000
  min_estimate_days: 0.5

scoring:
  velocity_by_module:
    trainer: 120
    parser: 80
    ui: 100
  pattern_factors:
    implement: 1.0
    refactor: 1.5
    test: 0.6

context:
  max_snippets: 5
  max_snippet_lines: 50
```

## See Also

- [INTEGRATION_GUIDE.md](../../INTEGRATION_GUIDE.md)
- [COMMAND_REFERENCE.md](../../COMMAND_REFERENCE.md)
- [TEMPLATE_UPDATE.md](../../TEMPLATE_UPDATE.md)