"""Minimize context for delegation to small LLMs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import ast

from ..parser.models import Task, DependencyGraph


@dataclass
class MinimalContext:
    task_id: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    required_interfaces: dict[str, str] = field(default_factory=dict)
    reference_snippets: list[dict] = field(default_factory=list)
    shared_config: dict = field(default_factory=dict)
    test_patterns: list[str] = field(default_factory=list)
    total_tokens: int = 0


def minimize_context(
    task: Task,
    graph: DependencyGraph,
    project_root: Path,
    max_tokens: int = 100000,
    max_snippets: int = 5,
    max_snippet_lines: int = 50
) -> MinimalContext:
    """Generate minimal context for a delegable task."""
    ctx = MinimalContext(
        task_id=task.id,
        description=task.description,
        acceptance_criteria=task.acceptance_criteria.copy(),
    )

    token_budget = max_tokens

    ctx.required_interfaces = extract_upstream_interfaces(task, graph, project_root)
    token_budget -= estimate_tokens(str(ctx.required_interfaces))

    ctx.reference_snippets = extract_reference_snippets(
        task, graph, project_root, max_snippets, max_snippet_lines
    )
    token_budget -= sum(s.get("tokens", 0) for s in ctx.reference_snippets)

    ctx.shared_config = extract_shared_config(task, project_root)
    token_budget -= estimate_tokens(str(ctx.shared_config))

    ctx.test_patterns = extract_test_patterns(task, project_root)
    token_budget -= estimate_tokens(str(ctx.test_patterns))

    ctx.total_tokens = max_tokens - max(token_budget, 0)

    return ctx


def extract_upstream_interfaces(task: Task, graph: DependencyGraph, project_root: Path) -> dict[str, str]:
    """Extract public interfaces from upstream tasks."""
    interfaces = {}

    for dep_id in task.dependencies:
        if dep_id not in graph.nodes:
            continue
        dep_task = graph.nodes[dep_id]
        if not dep_task.implementation_path:
            continue

        path = project_root / dep_task.implementation_path
        if not path.exists():
            continue

        if path.is_file() and path.suffix == '.py':
            interfaces.update(extract_python_interfaces(path, dep_task.module))
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                interfaces.update(extract_python_interfaces(py_file, dep_task.module))

    return interfaces


def extract_python_interfaces(filepath: Path, module: str) -> dict[str, str]:
    """Extract class/function signatures from Python file."""
    interfaces = {}
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    sig = get_function_signature(node)
                    key = f"{module}.{node.name}"
                    interfaces[key] = sig

            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith('_'):
                            methods.append(get_function_signature(item))
                    if methods:
                        key = f"{module}.{node.name}"
                        interfaces[key] = f"class {node.name}:\n" + "\n".join(f"    {m}" for m in methods)
    except Exception:
        pass

    return interfaces


def get_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Get function signature as string."""
    args = []
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)

    returns = ""
    if node.returns:
        returns = f" -> {ast.unparse(node.returns)}"

    async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{async_prefix}def {node.name}({', '.join(args)}){returns}"


def extract_reference_snippets(
    task: Task,
    graph: DependencyGraph,
    project_root: Path,
    max_snippets: int,
    max_lines: int
) -> list[dict]:
    """Extract relevant code snippets from the codebase."""
    snippets = []

    module_patterns = {
        "trainer": ["trainer", "training"],
        "parser": ["parser", "parse"],
        "model_manager": ["model", "manager"],
        "data_generator": ["generate", "data"],
        "ui": ["ui", "screen", "component"],
        "cli": ["cli", "command"],
        "core": ["core", "config"],
    }

    keywords = module_patterns.get(task.module, [task.module])
    task_words = set(task.description.lower().split())
    task_words.update(w for c in task.acceptance_criteria for w in c.lower().split())

    candidate_files = []
    for pattern in keywords:
        for py_file in project_root.rglob("*.py"):
            if pattern in str(py_file).lower():
                candidate_files.append(py_file)

    seen = set()
    for py_file in candidate_files:
        if len(snippets) >= max_snippets:
            break
        try:
            rel_path = str(py_file.relative_to(project_root))
            if rel_path in seen:
                continue

            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')

            scored_lines = []
            for i, line in enumerate(lines):
                score = sum(1 for w in task_words if w in line.lower())
                if score > 0:
                    scored_lines.append((score, i, line))

            scored_lines.sort(reverse=True, key=lambda x: x[0])

            for score, idx, _ in scored_lines[:3]:
                start = max(0, idx - max_lines // 2)
                end = min(len(lines), idx + max_lines // 2)
                snippet = '\n'.join(lines[start:end])
                tokens = len(snippet) // 4

                snippets.append({
                    "file": rel_path,
                    "lines": f"{start+1}-{end}",
                    "content": snippet,
                    "tokens": tokens,
                    "relevance": score
                })
                seen.add(rel_path)
                if len(snippets) >= max_snippets:
                    break
        except Exception:
            continue

    return snippets[:max_snippets]


def extract_shared_config(task: Task, project_root: Path) -> dict:
    """Extract relevant configuration."""
    config = {}
    config_files = [
        "pyproject.toml", "config.py", "settings.py",
        ".env.example", "requirements.txt"
    ]

    for cf in config_files:
        path = project_root / cf
        if path.exists():
            try:
                content = path.read_text(encoding='utf-8')
                if len(content) < 5000:
                    config[cf] = content[:2000]
            except Exception:
                pass

    return config


def extract_test_patterns(task: Task, project_root: Path) -> list[str]:
    """Extract test patterns relevant to the task."""
    patterns = []
    test_dirs = ["tests", "test"]

    for test_dir in test_dirs:
        test_path = project_root / test_dir
        if test_path.exists():
            for test_file in test_path.rglob("*.py"):
                try:
                    content = test_file.read_text(encoding='utf-8')
                    task_module = task.module.replace("/", "_")
                    if task_module in content.lower() or task.id.lower() in content.lower():
                        rel = str(test_file.relative_to(project_root))
                        patterns.append(f"{rel}: {content[:500]}")
                except Exception:
                    pass

    return patterns[:5]


def estimate_tokens(text: str) -> int:
    """Rough token estimation."""
    return len(text) // 4