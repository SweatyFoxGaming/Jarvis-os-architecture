import logging
from typing import List, Optional, Dict, Any

from src.capabilities.registry import CapabilityRegistry
from src.capabilities.manifest import CapabilityHealth
from src.capabilities.context import ExecutionContext

logger = logging.getLogger(__name__)


class CapabilityResolver:
    """
    Selects the best capability implementation for a given context.
    Scores based on health, confidence, version, resource cost, and priority.
    """

    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def resolve(self, desired_id: str, context: ExecutionContext) -> Optional[str]:
        """
        Returns the capability ID that best matches the desired capability.
        """
        # Get all manifests
        all_manifests = self.registry.get_all_manifests()
        candidates = [m for m in all_manifests if m.identity.id == desired_id or desired_id in m.classification.tags]

        if not candidates:
            logger.warning(f"No capability found for {desired_id}")
            return None

        # Score each candidate
        scored = []
        for manifest in candidates:
            cap_id = manifest.identity.id
            health = self.registry.get_health(cap_id)
            confidence = self.registry.get_confidence(cap_id)
            version = manifest.lifecycle.version
            resources = manifest.resources

            # Health score: healthy=1, degraded=0.5, offline=0
            health_score = 1.0 if health == CapabilityHealth.HEALTHY else 0.5 if health == CapabilityHealth.DEGRADED else 0.0

            # Resource cost (inverse, lower is better)
            cost_score = 1.0 / (1 + resources.estimated_tokens + resources.estimated_memory_mb / 128)

            # Confidence score (already 0-1)
            confidence_score = confidence

            # Version score (prefer higher)
            version_score = 0.5  # simplifed

            # Combined score (weights)
            score = 0.3 * health_score + 0.3 * confidence_score + 0.2 * cost_score + 0.1 * version_score
            scored.append((cap_id, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[0][0] if scored else None
        logger.info(f"[Resolver] Selected {best} with score {scored[0][1] if scored else 0}")
        return best
