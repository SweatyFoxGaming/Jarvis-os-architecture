"""
Evolution Platform – Recommendation Engine.
"""

import os
import logging
from typing import List, Optional

from src.evolution.models import AnalysisResult, Recommendation, RecommendationType, ApprovalState, AnalysisType

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generates actionable recommendations from analysis results.
    """

    def __init__(self):
        self.max_complexity = 10
        self.max_function_lines = 50
        self.max_module_lines = 500
        self.min_doc_ratio = 0.3
        self.duplication_threshold = 0.10

    def generate(self, analysis: AnalysisResult) -> List[Recommendation]:
        if analysis.type == AnalysisType.ARCHITECTURE:
            return self._generate_from_architecture(analysis)
        elif analysis.type == AnalysisType.CODE_QUALITY:
            return self._generate_from_quality(analysis)
        elif analysis.type == AnalysisType.PERFORMANCE:
            return self._generate_from_performance(analysis)
        elif analysis.type == AnalysisType.SECURITY:
            return self._generate_from_security(analysis)
        return []

    def _generate_from_architecture(self, analysis: AnalysisResult) -> List[Recommendation]:
        recommendations = []
        violations = analysis.violations

        layer_violations = {}
        for v in violations:
            source = v.get("source", "unknown")
            if source not in layer_violations:
                layer_violations[source] = []
            layer_violations[source].append(v)

        for source, vlist in layer_violations.items():
            if len(vlist) >= 3:
                targets = sorted(set(v.get("target", "unknown") for v in vlist))
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.ARCHITECTURAL_CHANGE,
                        title=f"Refactor dependencies from {source}",
                        description=f"Found {len(vlist)} dependency violations from {source} to {', '.join(targets)}.",
                        motivation="Maintains separation of concerns.",
                        evidence=f"Sample violations: {vlist[:3]}",
                        expected_benefit="Improved architecture clarity.",
                        expected_risk="May require significant refactoring.",
                        estimated_effort="medium",
                        affected_modules=[source] + targets,
                        governance_references=["Constitution", "Executive Model"],
                    )
                )
            else:
                for v in vlist:
                    recommendations.append(
                        Recommendation(
                            analysis_id=analysis.id,
                            type=RecommendationType.ARCHITECTURAL_CHANGE,
                            title=f"Fix architecture violation in {v.get('file', 'unknown')}",
                            description=v.get("violation", "Unknown violation"),
                            motivation="Governance compliance is required.",
                            evidence=str(v),
                            expected_benefit="Restores architectural integrity.",
                            expected_risk="Minimal.",
                            estimated_effort="low",
                            affected_modules=[v.get("source", "unknown"), v.get("target", "unknown")],
                            governance_references=["Constitution", "Executive Model"],
                        )
                    )

        return recommendations

    def _generate_from_quality(self, analysis: AnalysisResult) -> List[Recommendation]:
        recommendations = []
        metrics = analysis.metrics

        if metrics.get("avg_complexity", 0) > self.max_complexity:
            recommendations.append(
                Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType.REFACTOR,
                    title="Reduce code complexity",
                    description=f"Average cyclomatic complexity is {metrics['avg_complexity']:.2f}, above limit of {self.max_complexity}.",
                    motivation="Lower complexity improves testability and maintainability.",
                    evidence=f"Largest functions: {metrics.get('large_functions', [])[:3]}",
                    expected_benefit="Easier to maintain and test.",
                    expected_risk="May require careful refactoring.",
                    estimated_effort="medium",
                    affected_modules=[],
                    governance_references=["Constitution"],
                )
            )

        doc_ratio = metrics.get("doc_ratio", 1.0)
        if doc_ratio < self.min_doc_ratio:
            recommendations.append(
                Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType.DOCUMENTATION,
                    title="Improve documentation coverage",
                    description=f"Only {doc_ratio*100:.1f}% of functions have docstrings.",
                    motivation="Documentation helps maintenance and onboarding.",
                    evidence=f"Total functions: {metrics['total_functions']}, documented: {metrics['documented_functions']}",
                    expected_benefit="Better maintainability and onboarding.",
                    expected_risk="Minimal.",
                    estimated_effort="medium",
                    affected_modules=[],
                    governance_references=["Constitution"],
                )
            )

        large_files = metrics.get("large_files", [])
        if large_files:
            for lf in large_files[:3]:
                filename = os.path.basename(lf.get("file", ""))
                if filename.startswith("typing_extensions") or filename.startswith("threadpoolctl") or filename.startswith("six"):
                    continue
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.REFACTOR,
                        title=f"Split large file: {filename}",
                        description=f"File has {lf.get('lines', 0)} lines, exceeding limit of {self.max_module_lines}.",
                        motivation="Large files are harder to maintain.",
                        evidence=f"File: {lf}",
                        expected_benefit="Improved modularity.",
                        expected_risk="May require careful refactoring.",
                        estimated_effort="medium",
                        affected_modules=[lf.get("file", "")],
                        governance_references=["Constitution"],
                    )
                )

        duplication = metrics.get("duplication_estimate", 0.0)
        if duplication > self.duplication_threshold:
            recommendations.append(
                Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType.DUPLICATION,
                    title="Reduce code duplication",
                    description=f"Duplication estimate is {duplication*100:.1f}%.",
                    motivation="Duplication increases maintenance cost.",
                    evidence="Based on function body similarity analysis.",
                    expected_benefit="Easier to maintain and change.",
                    expected_risk="May require careful refactoring.",
                    estimated_effort="medium",
                    affected_modules=[],
                    governance_references=["Constitution"],
                )
            )

        mi = metrics.get("maintainability_index", 100)
        if mi < 50:
            recommendations.append(
                Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType.REFACTOR,
                    title="Improve maintainability",
                    description=f"Maintainability index is {mi:.1f} (target > 50).",
                    motivation="Higher maintainability means easier to modify.",
                    evidence=f"Doc ratio: {doc_ratio*100:.1f}%, avg complexity: {metrics.get('avg_complexity', 0):.2f}",
                    expected_benefit="Easier to maintain and extend.",
                    expected_risk="May require significant refactoring.",
                    estimated_effort="high",
                    affected_modules=[],
                    governance_references=["Constitution"],
                )
            )

        return recommendations

    def _generate_from_performance(self, analysis: AnalysisResult) -> List[Recommendation]:
        recommendations = []
        violations = analysis.violations
        metrics = analysis.metrics

        for v in violations:
            if "nested loop" in v.get("violation", "").lower():
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.PERFORMANCE,
                        title=f"Reduce nested loops in {v.get('function', 'function')}",
                        description=v.get("violation", ""),
                        motivation="Nested loops can cause O(n²) complexity.",
                        evidence=f"File: {v.get('file')}, line {v.get('line')}",
                        expected_benefit="Improved performance.",
                        expected_risk="May require algorithm redesign.",
                        estimated_effort="medium",
                        affected_modules=[v.get('file', '')],
                        governance_references=["Constitution"],
                    )
                )
            elif "recursion" in v.get("violation", "").lower():
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.PERFORMANCE,
                        title=f"Replace recursion in {v.get('function', 'function')}",
                        description=v.get("violation", ""),
                        motivation="Recursion can cause stack overflow and performance issues.",
                        evidence=f"File: {v.get('file')}, line {v.get('line')}",
                        expected_benefit="Improved performance and reliability.",
                        expected_risk="May require iterative implementation.",
                        estimated_effort="medium",
                        affected_modules=[v.get('file', '')],
                        governance_references=["Constitution"],
                    )
                )
            elif "Excessive imports" in v.get("violation", ""):
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.PERFORMANCE,
                        title="Reduce imports",
                        description=v.get("violation", ""),
                        motivation="Excessive imports increase startup time.",
                        evidence=f"File: {v.get('file')}",
                        expected_benefit="Faster startup.",
                        expected_risk="Minimal.",
                        estimated_effort="low",
                        affected_modules=[v.get('file', '')],
                        governance_references=["Constitution"],
                    )
                )

        if metrics.get("largest_function_lines", 0) > 200:
            recommendations.append(
                Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType.PERFORMANCE,
                    title="Break down very large functions",
                    description=f"Largest function has {metrics['largest_function_lines']} lines.",
                    motivation="Large functions are harder to optimize and maintain.",
                    evidence="Based on static analysis.",
                    expected_benefit="Better performance and maintainability.",
                    expected_risk="May require careful refactoring.",
                    estimated_effort="high",
                    affected_modules=[],
                    governance_references=["Constitution"],
                )
            )

        return recommendations

    def _generate_from_security(self, analysis: AnalysisResult) -> List[Recommendation]:
        recommendations = []
        violations = analysis.violations
        metrics = analysis.metrics

        for v in violations:
            if "Hardcoded secret" in v.get("violation", ""):
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.SECURITY,
                        title="Remove hardcoded secret",
                        description=v.get("violation", ""),
                        motivation="Hardcoded secrets are a major security risk.",
                        evidence=f"File: {v.get('file')}, line {v.get('line')}",
                        expected_benefit="Improved security posture.",
                        expected_risk="Minimal if using environment variables.",
                        estimated_effort="low",
                        affected_modules=[v.get('file', '')],
                        governance_references=["Constitution"],
                    )
                )
            elif "Unsafe function" in v.get("violation", ""):
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.SECURITY,
                        title="Replace unsafe function",
                        description=v.get("violation", ""),
                        motivation="Unsafe functions can lead to code injection.",
                        evidence=f"File: {v.get('file')}, line {v.get('line')}",
                        expected_benefit="Improved security.",
                        expected_risk="May require alternative implementation.",
                        estimated_effort="medium",
                        affected_modules=[v.get('file', '')],
                        governance_references=["Constitution"],
                    )
                )
            elif "unsafe module" in v.get("violation", "").lower():
                recommendations.append(
                    Recommendation(
                        analysis_id=analysis.id,
                        type=RecommendationType.SECURITY,
                        title="Review unsafe module import",
                        description=v.get("violation", ""),
                        motivation="Some modules have known security risks.",
                        evidence=f"File: {v.get('file')}, line {v.get('line')}",
                        expected_benefit="Reduced attack surface.",
                        expected_risk="May require alternative module.",
                        estimated_effort="medium",
                        affected_modules=[v.get('file', '')],
                        governance_references=["Constitution"],
                    )
                )

        if metrics.get("hardcoded_secrets", 0) > 0:
            recommendations.append(
                Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType.SECURITY,
                    title="Audit hardcoded secrets",
                    description=f"Found {metrics['hardcoded_secrets']} hardcoded secrets.",
                    motivation="All secrets must be stored securely.",
                    evidence="Static analysis detected secrets in code.",
                    expected_benefit="Eliminates credential leakage risk.",
                    expected_risk="Minimal.",
                    estimated_effort="low",
                    affected_modules=[],
                    governance_references=["Constitution"],
                )
            )

        return recommendations
