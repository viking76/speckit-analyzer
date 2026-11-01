"""Parser for speckit tasks.md format."""

import re
from pathlib import Path
from typing import Optional

from .models import Task, TaskStatus, Priority, DependencyGraph


TASK_PATTERN = re.compile(
    r'^###\s+(T\d+)\s+(.+?)\s*\n'
    r'(?:\*\*Phase\*\*:\s*(\d+)\s*\|\s*)?'
    r'(?:\*\*Module\*\*:\s*([^\|]+)\s*\|\s*)?'
    r'(?:\*\*Priority\*\*:\s*(\w+)\s*\|\s*)?'
    r'(?:\*\*Dependencies\*\*:\s*(\[.*?\])\s*\|\s*)?'
    r'(?:\*\*Estimate\*\*:\s*([\d.]+)\s*days?\s*)?\n'
    r'(?:\*\*Description\*\*:\s*(.+?)\s*\n)?'
    r'(?:\*\*Acceptance Criteria\*\*:\s*\n((?:- .+\n)*))?',
    re.MULTILINE | re.DOTALL
)

SIMPLE_TASK_PATTERN = re.compile(
    r'^###\s+(T\d+)\s+(.+?)(?:\n|$)',
    re.MULTILINE
)
# Support both markdown header format (### T001) and checked list format (- [ ] T001)
SIMPLE_TASK_LIST_PATTERN = re.compile(
    r'^- \[ \]? ?(T\d+)\s+(.+?)(?:\n|$)',
    re.MULTILINE
)

DEPENDENCIES_PATTERN = re.compile(
    r'\*\*Dependencies\*\*:\s*(\[.*?\]|None|none|TBD|tbd)',
    re.IGNORECASE
)

MERMAID_PATTERN = re.compile(
    r'```mermaid\n(.*?)\n```',
    re.DOTALL
)

MERMAID_EDGE_PATTERN = re.compile(
    r'(T\d+)\s*-->\s*(T\d+)'
)

STATUS_PATTERN = re.compile(
    r'\*\*Status\*\*:\s*(\w+)',
    re.IGNORECASE
)

IMPLEMENTATION_PATTERN = re.compile(
    r'\*\*Implementation\*\*:\s*(.+)',
    re.IGNORECASE
)

PARALLEL_MARKER = re.compile(r'\[P\]')
USER_STORY_PATTERN = re.compile(r'\[US(\d+)\]')


def parse_tasks_file(filepath: Path | str) -> tuple[list[Task], Optional[str]]:
    """Parse a tasks.md file and return tasks and mermaid graph."""
    path = Path(filepath)
    content = path.read_text(encoding='utf-8')
    return parse_tasks_content(content)


def parse_tasks_content(content: str) -> tuple[list[Task], Optional[str]]:
    """Parse tasks.md content and return tasks and mermaid graph."""
    tasks = []
    mermaid_raw = None

    mermaid_match = MERMAID_PATTERN.search(content)
    if mermaid_match:
        mermaid_raw = mermaid_match.group(1).strip()

    task_sections = split_task_sections(content)

    for section in task_sections:
        task = parse_task_section(section)
        if task:
            tasks.append(task)

    return tasks, mermaid_raw


def split_task_sections(content: str) -> list[str]:
    """Split content into individual task sections."""
    sections = []
    current_section = []
    in_task = False

    for line in content.split('\n'):
                # Reconnaître les deux formats : ### T001 et - [ ] T001
        if (line.startswith('### T') and len(line) > 5 and line[5].isdigit()) or \
           re.match(r'^- \[ \]? ?T\d+', line):
            if in_task and current_section:
                sections.append('\n'.join(current_section))
            current_section = [line]
            in_task = True
        elif in_task:
            current_section.append(line)

    if current_section:
        sections.append('\n'.join(current_section))

    return sections


def parse_task_section(section: str) -> Optional[Task]:
    """Parse a single task section."""
    lines = section.split('\n')
    if not lines:
        return None

    header = lines[0]
    match = SIMPLE_TASK_PATTERN.match(header)
    if not match:
    # Essayer le format liste cochée : - [ ] T001 ou - [X] T001
        match = SIMPLE_TASK_LIST_PATTERN.match(header)
        if not match:
            return None
    task_id = match.group(1)
    title = match.group(2).strip()

    task = Task(
        id=task_id,
        phase=0,
        module="unknown",
        priority=Priority.MEDIUM,
        description=title,
    )

    content = '\n'.join(lines[1:])

    phase_match = re.search(r'\*\*Phase\*\*:\s*(\d+)', content)
    if phase_match:
        task.phase = int(phase_match.group(1))

    module_match = re.search(r'\*\*Module\*\*:\s*([^\|]+)', content)
    if module_match:
        task.module = module_match.group(1).strip()

    priority_match = re.search(r'\*\*Priority\*\*:\s*(\w+)', content)
    if priority_match:
        try:
            task.priority = Priority(priority_match.group(1).capitalize())
        except ValueError:
            task.priority = Priority.MEDIUM

    deps_match = DEPENDENCIES_PATTERN.search(content)
    if deps_match:
        deps_str = deps_match.group(1)
        task.dependencies = parse_dependencies(deps_str)

    estimate_match = re.search(r'\*\*Estimate\*\*:\s*([\d.]+)\s*days?', content, re.IGNORECASE)
    if estimate_match:
        task.estimate_days = float(estimate_match.group(1))

    desc_match = re.search(r'\*\*Description\*\*:\s*(.+?)(?:\n\*\*|\n\n|$)', content, re.DOTALL)
    if desc_match:
        task.description = desc_match.group(1).strip()

    criteria_match = re.search(r'\*\*Acceptance Criteria\*\*:\s*\n((?:- .+\n)*)', content)
    if criteria_match:
        criteria_text = criteria_match.group(1)
        task.acceptance_criteria = [
            line.strip()[2:].strip() for line in criteria_text.strip().split('\n')
            if line.strip().startswith('- ')
        ]

    status_match = STATUS_PATTERN.search(content)
    if status_match:
        try:
            task.status = TaskStatus(status_match.group(1).upper())
        except ValueError:
            pass

    impl_match = IMPLEMENTATION_PATTERN.search(content)
    if impl_match:
        task.implementation_path = impl_match.group(1).strip()

    if PARALLEL_MARKER.search(section):
        task.parallel = True

    us_match = USER_STORY_PATTERN.search(section)
    if us_match:
        task.user_story = f"US{us_match.group(1)}"

    return task


def parse_dependencies(deps_str: str) -> list[str]:
    """Parse dependencies string like [T001, T002] or [dep1, dep2]."""
    deps_str = deps_str.strip('[]')
    if not deps_str:
        return []
    return [d.strip() for d in deps_str.split(',') if d.strip().startswith('T')]


def parse_mermaid_edges(mermaid: str) -> list[tuple[str, str]]:
    """Extract edges from mermaid graph."""
    edges = []
    for match in MERMAID_EDGE_PATTERN.finditer(mermaid):
        edges.append((match.group(1), match.group(2)))
    return edges


def build_dependency_graph(tasks: list[Task], mermaid_raw: Optional[str] = None) -> DependencyGraph:
    """Build dependency graph from tasks and optional mermaid."""
    graph = DependencyGraph()
    graph.nodes = {t.id: t for t in tasks}

    edges = set()
    for task in tasks:
        for dep in task.dependencies:
            edges.add((dep, task.id))

    if mermaid_raw:
        mermaid_edges = parse_mermaid_edges(mermaid_raw)
        for from_id, to_id in mermaid_edges:
            if from_id in graph.nodes and to_id in graph.nodes:
                edges.add((from_id, to_id))

    graph.edges = list(edges)
    graph.mermaid_raw = mermaid_raw

    return graph
