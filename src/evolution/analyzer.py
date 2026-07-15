"""
Evolution Platform – Architecture Analyzer.
"""

import os
import ast
import logging
import traceback
from typing import Dict, Any, List, Optional

from src.evolution.models import AnalysisResult, AnalysisType
from src.evolution.dependency_graph import DependencyGraph

logger = logging.getLogger(__name__)


class ArchitectureAnalyzer:
    """
    Analyzes the codebase for architectural compliance.
    Checks:
    - Dependency direction (layers)
    - Separation of concerns
    - Governance violations
    - Circular dependencies
    - Dependency graph
    """

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.layer_rules = {
            "src.executive": ["src.cognition", "src.capability", "src.execution", "src.environment", "src.core"],
            "src.cognition": ["src.capability", "src.execution", "src.environment", "src.core", "src.memory"],
            "src.capability": ["src.execution", "src.environment", "src.core"],
            "src.execution": ["src.environment", "src.core"],
            "src.environment": ["src.core"],
            "src.core": [],
            "src.interaction": ["src.executive", "src.core"],
            "src.voice": ["src.core"],
            "src.memory": ["src.core"],
        }
        self.allowed_imports = ["src.capabilities.providers.builtin"]

    def analyze(self) -> AnalysisResult:
        """Run the architecture analysis."""
        try:
            dep_graph = DependencyGraph(self.root_path)
            dep_graph.build()

            cycles = dep_graph.find_cycles()
            violations = []
            metrics = {
                "total_files": 0,
                "total_modules": 0,
                "violations": 0,
                "circular_dependencies": len(cycles),
            }

            for dirpath, _, filenames in os.walk(self.root_path):
                for filename in filenames:
                    if filename.endswith(".py") and not filename.startswith("__"):
                        filepath = os.path.join(dirpath, filename)
                        metrics["total_files"] += 1
                        violations.extend(self._check_file(filepath))

            metrics["violations"] = len(violations)
            graph_json = dep_graph.export_json()

            return AnalysisResult(
                type=AnalysisType.ARCHITECTURE,
                summary=f"Found {len(violations)} layer violations, {len(cycles)} circular dependencies.",
                details={
                    "layer_rules": self.layer_rules,
                    "violations_sample": violations[:10],
                    "cycles_sample": cycles[:5],
                },
                metrics=metrics,
                violations=violations,
                circular_dependencies=cycles,
                dependency_graph=graph_json,
            )
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}", exc_info=True)
            return AnalysisResult(
                type=AnalysisType.ARCHITECTURE,
                summary=f"Analysis failed: {str(e)}",
                details={"error": str(e), "traceback": traceback.format_exc()},
                metrics={},
                violations=[],
                circular_dependencies=[],
                dependency_graph=None,
            )

    def _check_file(self, filepath: str) -> List[Dict]:
        """Check a single file for import violations."""
        violations = []
        relative_path = filepath.replace(self.root_path, "").lstrip("/")
        source_layer = self._detect_layer(relative_path)

        if not source_layer:
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except SyntaxError as e:
            logger.warning(f"Syntax error in {filepath}: {e}")
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not module.startswith("src."):
                    continue

                target_layer = self._detect_layer(module)
                if not target_layer:
                    continue

                if target_layer != source_layer and target_layer not in self.layer_rules.get(source_layer, []):
                    if module not in self.allowed_imports:
                        violations.append({
                            "file": relative_path,
                            "line": node.lineno,
                            "violation": f"Layer violation: {source_layer} imports {target_layer} ({module})",
                            "source": source_layer,
                            "target": target_layer,
                            "module": module,
                        })

        return violations

    def _detect_layer(self, path_or_module: str) -> Optional[str]:
        """Detect the layer of a path or module."""
        module = path_or_module.replace("/", ".").replace("\\", ".")
        if module.endswith(".py"):
            module = module[:-3]
        if module.endswith(".__init__"):
            module = module[:-9]

        for layer in self.layer_rules:
            if module.startswith(layer):
                return layer
        return None
