"""
Evolution Platform – Dependency Graph utilities.
"""

import ast
import os
import logging
from typing import Dict, Set, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class DependencyGraph:
    """
    Builds and analyzes dependency graph from source code.
    """

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.nodes: Set[str] = set()
        self.module_to_file: Dict[str, str] = {}

    def build(self) -> None:
        """Scan all Python files and build the dependency graph."""
        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("__"):
                    filepath = os.path.join(dirpath, filename)
                    module = self._filepath_to_module(filepath)
                    if module:
                        self.nodes.add(module)
                        self.module_to_file[module] = filepath
                        deps = self._extract_imports(filepath)
                        for dep in deps:
                            if dep in self.nodes or self._is_src_module(dep):
                                self.graph[module].add(dep)
                                self.reverse_graph[dep].add(module)

        logger.info(f"[DependencyGraph] Built graph with {len(self.nodes)} nodes and {sum(len(v) for v in self.graph.values())} edges.")

    def _filepath_to_module(self, filepath: str) -> Optional[str]:
        """Convert filepath to Python module name."""
        rel = os.path.relpath(filepath, self.root_path)
        if rel.startswith(".."):
            return None
        module = rel.replace(os.sep, ".").replace("/", ".").replace("\\", ".")
        if module.endswith(".py"):
            module = module[:-3]
        if module.endswith(".__init__"):
            module = module[:-9]
        if module.startswith("src.") or module.startswith("src"):
            return module
        return None

    def _is_src_module(self, module: str) -> bool:
        """Check if module is within src/."""
        return module.startswith("src.") or module.startswith("src")

    def _extract_imports(self, filepath: str) -> Set[str]:
        """Extract imported modules from a Python file."""
        imports = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                return imports
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if self._is_src_module(alias.name):
                            imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and self._is_src_module(node.module):
                        imports.add(node.module)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {filepath}: {e}")
        except Exception as e:
            logger.warning(f"Failed to parse {filepath}: {e}")
        return imports

    def find_cycles(self) -> List[List[str]]:
        """
        Find all cycles in the dependency graph using iterative DFS.
        Returns list of cycles (each cycle is a list of module names).
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in self.graph.get(node, []):
                if neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor, path[:])
            rec_stack.remove(node)
            path.pop()

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])
        return cycles

    def export_json(self) -> dict:
        """Export graph as JSON-serializable dict."""
        return {
            "nodes": list(self.nodes),
            "edges": [
                {"source": src, "target": dst}
                for src, deps in self.graph.items()
                for dst in deps
            ],
            "module_to_file": self.module_to_file,
        }
