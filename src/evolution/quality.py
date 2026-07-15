"""
Evolution Platform – Code Quality Analyzer.
"""

import os
import ast
import logging
import hashlib
from collections import defaultdict
from typing import Dict, Any, List, Set, Tuple, Optional

from src.evolution.models import AnalysisResult, AnalysisType

logger = logging.getLogger(__name__)


class CodeQualityAnalyzer:
    """
    Analyzes code quality metrics:
    - Cyclomatic complexity (function & module)
    - Function size (lines)
    - Module size (lines)
    - Documentation coverage
    - Duplication (basic estimate using line-based similarity)
    - Maintainability index (simplified)
    """

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.max_complexity = 10
        self.max_function_lines = 50
        self.max_module_lines = 500
        self.min_doc_ratio = 0.3
        self.duplication_threshold = 0.10  # 10% duplication rate trigger

    def analyze(self) -> AnalysisResult:
        """Run the code quality analysis."""
        metrics = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "documented_functions": 0,
            "avg_complexity": 0,
            "max_complexity": 0,
            "complexities": [],
            "large_functions": [],
            "large_files": [],
            "module_metrics": {},  # module -> {lines, functions, complexity, docs}
            "maintainability_index": 0,
            "duplication_estimate": 0,
        }

        # Collect all function bodies for duplication detection
        all_function_bodies: List[Tuple[str, str, str]] = []  # (file, function_name, normalized_body)

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("__"):
                    filepath = os.path.join(dirpath, filename)
                    metrics["total_files"] += 1
                    self._analyze_file(filepath, metrics, all_function_bodies)

        # Compute aggregates
        if metrics["total_functions"] > 0:
            metrics["avg_complexity"] = sum(metrics["complexities"]) / len(metrics["complexities"])
            metrics["max_complexity"] = max(metrics["complexities"])
        else:
            metrics["avg_complexity"] = 0
            metrics["max_complexity"] = 0

        if metrics["total_functions"] > 0:
            metrics["doc_ratio"] = metrics["documented_functions"] / metrics["total_functions"]
        else:
            metrics["doc_ratio"] = 0

        # Compute maintainability index (simplified)
        metrics["maintainability_index"] = self._compute_maintainability_index(metrics)

        # Compute duplication estimate
        metrics["duplication_estimate"] = self._compute_duplication_estimate(all_function_bodies)

        # Identify issues
        health_issues = []
        if metrics["avg_complexity"] > self.max_complexity:
            health_issues.append(f"High average complexity ({metrics['avg_complexity']:.2f})")
        if len(metrics["large_functions"]) > 0:
            health_issues.append(f"{len(metrics['large_functions'])} functions exceed {self.max_function_lines} lines")
        if len(metrics["large_files"]) > 0:
            health_issues.append(f"{len(metrics['large_files'])} files exceed {self.max_module_lines} lines")
        if metrics["doc_ratio"] < self.min_doc_ratio:
            health_issues.append(f"Low documentation coverage ({metrics['doc_ratio']*100:.1f}%)")
        if metrics["duplication_estimate"] > self.duplication_threshold:
            health_issues.append(f"Duplication estimate {metrics['duplication_estimate']*100:.1f}% above threshold")

        return AnalysisResult(
            type=AnalysisType.CODE_QUALITY,
            summary=f"Analyzed {metrics['total_files']} files, {metrics['total_lines']} lines, {metrics['total_functions']} functions. Issues: {len(health_issues)}.",
            details={
                "health_issues": health_issues,
                "large_functions_sample": metrics["large_functions"][:10],
                "large_files_sample": metrics["large_files"][:10],
            },
            metrics=metrics,
        )

    def _analyze_file(self, filepath: str, metrics: Dict[str, Any], all_function_bodies: List[Tuple[str, str, str]]) -> None:
        """Analyze a single file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            return

        lines = content.splitlines()
        metrics["total_lines"] += len(lines)

        if len(lines) > self.max_module_lines:
            metrics["large_files"].append({
                "file": filepath,
                "lines": len(lines),
            })

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        module_name = self._module_from_path(filepath)
        module_metrics = {
            "lines": len(lines),
            "functions": 0,
            "complexity": 0,
            "docs": 0,
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics["total_functions"] += 1
                module_metrics["functions"] += 1
                doc = ast.get_docstring(node)
                if doc:
                    metrics["documented_functions"] += 1
                    module_metrics["docs"] += 1

                func_lines = node.end_lineno - node.lineno + 1
                if func_lines > self.max_function_lines:
                    metrics["large_functions"].append({
                        "file": filepath,
                        "function": node.name,
                        "lines": func_lines,
                    })

                complexity = self._compute_complexity(node)
                metrics["complexities"].append(complexity)
                module_metrics["complexity"] += complexity

                # Store for duplication detection
                try:
                    body = ast.unparse(node)
                    normalized = self._normalize_code(body)
                    all_function_bodies.append((filepath, node.name, normalized))
                except Exception:
                    pass

            elif isinstance(node, ast.ClassDef):
                metrics["total_classes"] += 1

        # Store module metrics
        if module_name:
            metrics["module_metrics"][module_name] = module_metrics

    def _compute_complexity(self, func: ast.FunctionDef) -> int:
        """Compute cyclomatic complexity for a function."""
        complexity = 1
        for node in ast.walk(func):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers)
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity

    def _module_from_path(self, filepath: str) -> Optional[str]:
        """Extract module name from filepath."""
        rel = os.path.relpath(filepath, self.root_path)
        module = rel.replace(os.sep, ".").replace("/", ".").replace("\\", ".")
        if module.endswith(".py"):
            module = module[:-3]
        if module.endswith(".__init__"):
            module = module[:-9]
        if module.startswith("src.") or module.startswith("src"):
            return module
        return None

    def _normalize_code(self, code: str) -> str:
        """Normalize code by stripping whitespace and comments."""
        lines = []
        for line in code.splitlines():
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            if line:
                lines.append(line)
        return ' '.join(lines)

    def _compute_duplication_estimate(self, function_bodies: List[Tuple[str, str, str]]) -> float:
        """
        Compute duplication estimate based on function body similarity.
        Uses a simple Jaccard-like approach on normalized bodies.
        """
        if len(function_bodies) < 2:
            return 0.0

        # Sample up to 1000 functions
        sample_size = min(1000, len(function_bodies))
        sampled = function_bodies[:sample_size]

        duplicates = 0
        comparisons = 0
        # Compare first 500 functions with a limited window
        for i in range(min(500, len(sampled))):
            _, _, body_i = sampled[i]
            tokens_i = set(body_i.split())
            if not tokens_i:
                continue
            for j in range(i+1, min(i+50, len(sampled))):
                _, _, body_j = sampled[j]
                tokens_j = set(body_j.split())
                if not tokens_j:
                    continue
                jaccard = len(tokens_i & tokens_j) / len(tokens_i | tokens_j)
                if jaccard > 0.7:
                    duplicates += 1
                comparisons += 1

        if comparisons == 0:
            return 0.0
        return duplicates / comparisons

    def _compute_maintainability_index(self, metrics: Dict[str, Any]) -> float:
        """
        Compute a simplified maintainability index.
        Higher is better.
        """
        doc = metrics.get("doc_ratio", 0)
        avg_complexity = metrics.get("avg_complexity", 0)
        # Compute average function size
        large_funcs = metrics.get("large_functions", [])
        if large_funcs:
            avg_size = sum(f.get("lines", 0) for f in large_funcs) / len(large_funcs)
        else:
            avg_size = 0
        complexity_score = max(0, 1 - (avg_complexity / 20))
        size_score = max(0, 1 - (avg_size / 100))
        maintainability = (doc * 0.4) + (complexity_score * 0.3) + (size_score * 0.3)
        return maintainability * 100
