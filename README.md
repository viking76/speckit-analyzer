<p align="center">
  <img src="https://raw.githubusercontent.com/viking76/speckit-analyzer/main/assets/logo.svg" alt="speckit-analyzer" width="180" />
</p>

<h1 align="center">speckit-analyzer</h1>

<p align="center">
  <strong>Task scoring, dependency analysis & delegation packaging for speckit</strong>
</p>

<p align="center">
  <a href="#-quick-start"><strong>Quick Start</strong></a> •
  <a href="#-features"><strong>Features</strong></a> •
  <a href="#-installation"><strong>Installation</strong></a> •
  <a href="#-usage"><strong>Usage</strong></a> •
  <a href="#-outputs"><strong>Outputs</strong></a> •
  <a href="#-docs"><strong>Documentation</strong></a>
</p>

<p align="center">
  <a href="https://github.com/viking76/speckit-analyzer/actions"><img src="https://img.shields.io/github/actions/workflow/status/viking76/speckit-analyzer/ci.yml?style=flat-square" alt="CI" /></a>
  <a href="https://pypi.org/project/speckit-analyzer"><img src="https://img.shields.io/pypi/v/speckit-analyzer?style=flat-square" alt="PyPI" /></a>
  <a href="https://github.com/viking76/speckit-analyzer/blob/main/LICENSE"><img src="https://img.shields.io/github/license/viking76/speckit-analyzer?style=flat-square" alt="License" /></a>
  <a href="https://github.com/viking76/speckit-analyzer"><img src="https://img.shields.io/github/stars/viking76/speckit-analyzer?style=flat-square" alt="Stars" /></a>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🎯 Heuristic Scoring** | Complexity (1-10), LOC estimation, context tokens — zero LLM calls |
| **📊 Dependency Graph** | DAG from `Dependencies:` + Mermaid, topological sort, cycle detection |
| **⚡ Critical Path** | Longest weighted path, bottleneck detection, parallelization opportunities |
| **🔗 Context Propagation** | Upstream/downstream file context per task (configurable depth) |
| **📦 Delegation Packaging** | Minimal context (< 100k tokens) for small LLM (4B) delegation |
| **📈 Threshold Analysis** | Precision/recall/F1 sweep across complexity/context thresholds |
| **📜 Statistics History** | CSV/Parquet tracking across runs for trend analysis |
| **🎓 Ground Truth Calibration** | Learns from `COMPLETED` tasks with actual implementations |

---

## 🚀 Quick Start

```bash
# 1. Install in your speckit project
cd /your/speckit/project
./.specify/scripts/bash/integrate-analyze.sh

# 2. Analyze tasks for delegation
/speckit.analyze

# 3. Review delegation candidates
cat specs/001-feature/analysis/task_tree.md

# 4. Delegate to small LLM
cat specs/001-feature/analysis/delegation_package/T203/context.md
```

---

## 📦 Installation

### Standalone Package
```bash
pip install speckit-analyzer
```

### In speckit Project (Recommended)
```bash
# From your speckit repo root
./.specify/scripts/bash/integrate-analyze.sh
```

This installs:
- `speckit-analyze` — main CLI command
- `analyze-tasks.sh` / `speckit-analyze` — bash wrappers
- `integrate-analyze.sh` — one-command setup
- Updated `tasks-template.md` with Score/Delegation section
- `analysis-template.md` for reports

---

## 🎮 Usage

### Basic Analysis
```bash
# Current feature (auto-detect on feature branch)
/speckit.analyze

# Specific tasks file
/speckit.analyze specs/003-ai-linux-iso/tasks.md
```

### With Calibration
```bash
# Calibrate from COMPLETED tasks with actual implementations
/speckit.analyze --calibrate
```

### Custom Thresholds
```bash
# Conservative: only very simple tasks
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

---

## 📁 Outputs

All artifacts in `specs/###-feature/analysis/`:

```
analysis/
├── analysis.json                 # Complete machine-readable result
├── task_tree.md                  # Visual tree with scores + critical path
├── task_list.csv                 # Spreadsheet-ready task list
├── critical_path.md              # Critical path + parallelization
├── dependency_graph.mmd          # Mermaid graph (color-coded by score)
├── dependency_graph_phases.mmd   # Mermaid grouped by phase
├── threshold_analysis.md         # Threshold sweep report
├── threshold_analysis.csv        # Threshold data for plotting
├── stats_history.csv             # Historical stats across runs
├── stats_history.parquet         # Efficient Parquet for Pandas
└── delegation_package/
    ├── index.md                  # Package index
    └── T###/
        ├── context.md            # Minimal context for delegation
        ├── interfaces.json       # Required upstream signatures
        ├── metadata.json         # Scores, deps, thresholds
        ├── refs/                 # 3-5 relevant code snippets
        └── tests.md              # Expected test patterns
```

### Delegation Package Example

```markdown
# Delegation Context: T203

## Description
Add real-time metrics collection during training

## Acceptance Criteria
1. Loss tracking per batch
2. Accuracy and F1-score calculation
3. Metrics aggregation and smoothing
4. Performance impact <5%

## Required Interfaces (from upstream)
### trainer.MetricsCallback
```python
class MetricsCallback:
    def on_batch_end(self, batch: int, logs: Dict[str, float]) -> None
    def on_epoch_end(self, epoch: int, logs: Dict[str, float]) -> None
```

## Reference Snippets
### ref_1_trainer.py (lines 45-78)
```python
class MetricsCallback:
    def __init__(self):
        self.batch_losses = []
        self.epoch_metrics = {}
    ...
```

## Shared Configuration
### config.py
```python
METRICS_SMOOTHING_WINDOW = 10
METRICS_UPDATE_INTERVAL = 1.0
```

## Total Estimated Tokens: 12,400
```

---

## 📚 Documentation

| Doc | Description |
|-----|-------------|
| [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) | Complete `/speckit.analyze` CLI reference |
| [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) | Full integration guide for speckit projects |
| [TEMPLATE_UPDATE.md](TEMPLATE_UPDATE.md) | Template modification details |

---

## ⚙️ Configuration

Create `.speckit-analyzer.yaml` at repo root:

```yaml
llm:
  base_url: "http://192.168.1.162:8889/v1"  # Unsloth endpoint
  model: "qwen2.5-4b-instruct"
  timeout: 60

thresholds:
  complexity: 5          # Max complexity for delegation (1-10)
  context_tokens: 100000 # Max context tokens for delegation
  min_estimate_days: 0.5

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
```

---

## 🏗 Architecture

```
speckit_analyzer/
├── parser/           # tasks.md → Task objects + Mermaid parsing
├── scoring/          # Heuristics + calibration from ground truth
├── graph/            # NetworkX DAG, critical path, context propagation
├── context/          # Context minimization + packaging
├── enricher/         # tasks.md enrichment with scores
├── output/           # JSON, Markdown, Mermaid, CSV, Parquet
├── stats/            # Statistics collection + threshold sweeping
└── cli.py            # Typer CLI entry point
```

---

## 🧪 Calibration from Ground Truth

Improve estimation accuracy:

```bash
# Requires tasks with:
# - status: COMPLETED
# - Implementation: path/to/actual/code.py
/speckit.analyze --calibrate
```

Learns from actual implementations:
- Real LOC, cyclomatic complexity, context tokens
- Velocity per module (LOC/day)
- Pattern factors
- Correlation metrics (complexity vs actual LOC)

---

## 📊 Threshold Tuning

```bash
# Full sweep
/speckit.analyze --sweep

# Check results
cat analysis/threshold_analysis.md
```

| Complexity | Delegable | Precision | Recall | F1 |
|------------|-----------|-----------|--------|-----|
| 3 | 8 | 0.75 | 0.40 | 0.52 |
| 4 | 15 | 0.73 | 0.65 | 0.69 |
| **5** | **23** | **0.70** | **0.85** | **0.77** |
| 6 | 31 | 0.61 | 0.95 | 0.74 |

---

## 🤝 Contributing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
mypy speckit_analyzer
```

---

## 📄 License

Apache-2.0 — Part of the [speckit](https://github.com/viking76/speckit) ecosystem.

---

<p align="center">
  Made with ❤️ for the speckit community
</p>