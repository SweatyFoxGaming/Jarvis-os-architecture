"""
Evolution Platform – Performance Analyzer.
Static analysis for potential performance issues.
"""

import os
import ast
import logging
from typing import Dict, Any, List

from src.evolution.models import AnalysisResult, AnalysisType

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Analyzes code for potential performance issues:
    - Nested loops (O(n^2) complexity)
    - Deep recursion
    - Large function bodies
    - Excessive imports
    - Heavy operations (try-except, etc.)
    """

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.max_nesting_depth = 3

    def analyze(self) -> AnalysisResult:
        """Run the performance analysis."""
        metrics = {
            "total_files": 0,
            "functions_with_nested_loops": 0,
            "functions_with_deep_recursion": 0,
            "largest_function_lines": 0,
            "excessive_imports": 0,
            "total_functions": 0,
        }
        violations = []

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("__"):
                    filepath = os.path.join(dirpath, filename)
                    metrics["total_files"] += 1
                    self._analyze_file(filepath, metrics, violations)

        return AnalysisResult(
            type=AnalysisType.PERFORMANCE,
            summary=f"Found {len(violations)} performance concerns across {metrics['total_files']} files.",
            details={
                "violations_sample": violations[:10],
                "metrics": metrics,
            },
            metrics=metrics,
            violations=violations,
        )

    def _analyze_file(self, filepath: str, metrics: Dict[str, Any], violations: List[Dict]) -> None:
        """Analyze a single file for performance issues."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                return
            tree = ast.parse(content)
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics["total_functions"] += 1
                # Check nested loops
                depth = self._get_nesting_depth(node)
                if depth > self.max_nesting_depth:
                    metrics["functions_with_nested_loops"] += 1
                    violations.append({
                        "file": filepath,
                        "function": node.name,
                        "line": node.lineno,
                        "violation": f"Nested loop depth {depth} (limit {self.max_nesting_depth})",
                        "severity": "medium",
                    })

                # Check recursion
                if self._has_recursion(node):
                    metrics["functions_with_deep_recursion"] += 1
                    violations.append({
                        "file": filepath,
                        "function": node.name,
                        "line": node.lineno,
                        "violation": "Recursive function detected (potential stack/performance issue)",
                        "severity": "low",
                    })

                # Check function length
                func_lines = node.end_lineno - node.lineno + 1
                if func_lines > metrics["largest_function_lines"]:
                    metrics["largest_function_lines"] = func_lines

        # Check for excessive imports
        import_count = len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))])
        if import_count > 20:
            metrics["excessive_imports"] += 1
            violations.append({
                "file": filepath,
                "line": 1,
                "violation": f"Excessive imports ({import_count}) in file",
                "severity": "low",
            })

    def _get_nesting_depth(self, node: ast.FunctionDef) -> int:
        """Compute max nesting depth of loops inside a function."""
        max_depth = 0

        def walk(n, depth):
            nonlocal max_depth
            if isinstance(n, (ast.For, ast.While)):
                depth += 1
                if depth > max_depth:
                    max_depth = depth
            for child in ast.iter_child_nodes(n):
                walk(child, depth)

        walk(node, 0)
        return max_depth

    def _has_recursion(self, node: ast.FunctionDef) -> bool:
        """Check if a function recursively calls itself."""
        func_name = node.name
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == func_name:
                    return True
        return False
