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
  <a href="#-configuration"><strong>Configuration</strong></a> •
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
| **🪝 Auto-hooks** | Runs automatically after `/speckit.tasks` |

---

## 🚀 Quick Start

```bash
# 1. In your speckit project root
specify extension add /path/to/speckit-analyzer/specify-extension/speckit-analyzer --dev

# 2. Analyze tasks for delegation
.specify/extensions/speckit-analyzer/scripts/analyze-tasks.sh specs/001-feature/tasks.md

# 3. Review delegation candidates
cat specs/001-feature/analysis/task_tree.md

# 4. Delegate to small LLM (4B)
cat specs/001-feature/analysis/delegation_package/T203/context.md
```

---

## 📦 Installation

### Via spec-kit Extension System (Recommended)

```bash
# From your speckit project root
specify extension add /path/to/speckit-analyzer/specify-extension/speckit-analyzer --dev
```

This installs the extension into `.specify/extensions/speckit-analyzer/` with:

- **Command**: `speckit.speckit-analyzer.analyze` (available in AI coding agents)
- **Bash wrapper**: `.specify/extensions/speckit-analyzer/scripts/analyze-tasks.sh`
- **Auto-hooks**: Runs after `/speckit.tasks` (optional, prompted)
- **Config**: `.specify/extensions/speckit-analyzer/speckit-analyzer-config.yml`
- **Templates**: Updated `tasks-template.md` with Score/Delegation section

### Standalone (Without spec-kit)

```bash
pip install speckit-analyzer
```

---

## 🎮 Usage

### Basic Analysis (Bash)

```bash
# Current feature (auto-detect on feature branch)
.specify/extensions/speckit-analyzer/scripts/analyze-tasks.sh

# Specific tasks file
.specify/extensions/speckit-analyzer/scripts/analyze-tasks.sh specs/003-ai-linux-iso/tasks.md
```

### In AI Coding Agent

```bash
# Available as slash command after extension install
/speckit.speckit-analyzer.analyze

# With options
/speckit.speckit-analyzer.analyze --calibrate --sweep --threshold complexity=4,context=80000
```

### Options

| Option | Description |
|--------|-------------|
| `--calibrate` | Calibrate from `COMPLETED` tasks with actual implementations |
| `--threshold STR` | Delegation thresholds `complexity=X,context=Y` (default: `5,100000`) |
| `--sweep` | Full threshold sweep (precision/recall/F1) |
| `--enrich` | Annotate tasks.md with scores inline |
| `--json` | Output JSON to stdout |
| `--stats-history` | Update stats history (CSV/Parquet) |
| `-v, --verbose` | Verbose output |

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

## ⚙️ Configuration

Create `.specify/extensions/speckit-analyzer/speckit-analyzer-config.yml`:

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

---

## 🏗 Architecture

```
specify-extension/speckit-analyzer/
├── extension.yml           # Manifest (schema_version 1.0)
├── commands/analyze.md     # Command documentation
├── scripts/
│   ├── analyze-tasks.sh    # Bash wrapper
│   ├── analyze.py          # Python CLI entry (cli:app)
│   ├── initialize.py       # session_start event
│   └── validate.py         # pre_tool_use event
├── hooks/
│   ├── auto-analyze.yaml   # after_tasks hook
│   └── auto-enrich.yaml    # after_tasks hook
├── templates/
│   ├── tasks-template.md   # Enhanced with Score/Delegation
│   └── analysis-template.md
├── config/
│   └── speckit-analyzer-config.template.yml
└── speckit_analyzer/       # Python package
    ├── parser/             # tasks.md parsing + Mermaid
    ├── scoring/            # Heuristics + calibration
    ├── graph/              # NetworkX DAG, critical path
    ├── context/            # Minimization + packaging
    ├── enricher/           # tasks.md enrichment
    ├── output/             # JSON, MD, Mermaid, CSV, Parquet
    └── stats/              # Statistics + threshold sweeping
```

---

## 🧪 Calibration from Ground Truth

Improve estimation accuracy using completed tasks:

```bash
# Requires tasks with:
# - status: COMPLETED
# - Implementation: path/to/actual/code.py
/speckit.speckit-analyzer.analyze --calibrate
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
/speckit.speckit-analyzer.analyze --sweep

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