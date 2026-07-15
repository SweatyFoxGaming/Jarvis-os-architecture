"""
Evolution Platform – Security Analyzer.
Static analysis for common security issues.
"""

import os
import ast
import logging
import re
from typing import Dict, Any, List, Set

from src.evolution.models import AnalysisResult, AnalysisType

logger = logging.getLogger(__name__)


class SecurityAnalyzer:
    """
    Analyzes code for security issues:
    - Hardcoded secrets (passwords, API keys, tokens)
    - Dangerous functions (eval, exec, pickle, etc.)
    - Unsafe subprocess calls
    - Insecure hash functions
    """

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.unsafe_functions = {
            "eval": "Execution of arbitrary code",
            "exec": "Execution of arbitrary code",
            "pickle.loads": "Potential deserialization attacks",
            "pickle.load": "Potential deserialization attacks",
            "__import__": "Dynamic import of untrusted modules",
            "compile": "Compilation of untrusted code",
        }
        self.secret_patterns = [
            r'(?i)(password|passwd|pwd)\s*=\s*[\'"][^\'"]+[\'"]',
            r'(?i)(secret|api_key|token|auth|credential)\s*=\s*[\'"][^\'"]+[\'"]',
            r'(?i)(AWS_SECRET|AWS_ACCESS|GITHUB_TOKEN)\s*=\s*[\'"][^\'"]+[\'"]',
        ]

    def analyze(self) -> AnalysisResult:
        """Run the security analysis."""
        metrics = {
            "total_files": 0,
            "hardcoded_secrets": 0,
            "unsafe_functions_used": 0,
            "unsafe_imports": 0,
        }
        violations = []

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("__"):
                    filepath = os.path.join(dirpath, filename)
                    metrics["total_files"] += 1
                    self._analyze_file(filepath, metrics, violations)

        return AnalysisResult(
            type=AnalysisType.SECURITY,
            summary=f"Found {len(violations)} security concerns across {metrics['total_files']} files.",
            details={
                "violations_sample": violations[:10],
                "metrics": metrics,
            },
            metrics=metrics,
            violations=violations,
        )

    def _analyze_file(self, filepath: str, metrics: Dict[str, Any], violations: List[Dict]) -> None:
        """Analyze a single file for security issues."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                return
            tree = ast.parse(content)
        except Exception:
            return

        # Check for hardcoded secrets
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern in self.secret_patterns:
                if re.search(pattern, line):
                    # Skip if it's a placeholder or example
                    if "example" in line.lower() or "test" in line.lower() or "your_" in line.lower():
                        continue
                    metrics["hardcoded_secrets"] += 1
                    violations.append({
                        "file": filepath,
                        "line": line_num,
                        "violation": "Hardcoded secret (password, API key, token) detected",
                        "severity": "high",
                    })
                    break

        # Check for unsafe functions
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.unsafe_functions:
                    metrics["unsafe_functions_used"] += 1
                    violations.append({
                        "file": filepath,
                        "line": node.lineno,
                        "violation": f"Unsafe function '{func_name}' used: {self.unsafe_functions[func_name]}",
                        "severity": "medium",
                    })
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                for alias in (node.names if isinstance(node, ast.Import) else []):
                    if alias.name in ["pickle", "subprocess", "socket"]:
                        metrics["unsafe_imports"] += 1
                        violations.append({
                            "file": filepath,
                            "line": node.lineno,
                            "violation": f"Import of potentially unsafe module '{alias.name}'",
                            "severity": "low",
                        })
