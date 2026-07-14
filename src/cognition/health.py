import logging
from typing import Dict, Any
from datetime import datetime

from src.cognition.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


class CognitiveHealthMonitor:
    """
    Monitors the health of the Cognitive Platform.
    """

    def __init__(self, knowledge_store: KnowledgeStore):
        self.knowledge_store = knowledge_store
        logger.info("[CognitiveHealthMonitor] Initialized.")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Collect and return health metrics.
        """
        all_knowledge = self.knowledge_store.get_all(limit=1000)
        total = len(all_knowledge)
        if total == 0:
            return {"total": 0, "status": "empty"}

        types = {}
        total_confidence = 0.0
        verified = 0
        for k in all_knowledge:
            types[k.type.value] = types.get(k.type.value, 0) + 1
            total_confidence += k.confidence
            if k.verification_status.value in ["verified_by_llm", "verified_by_human"]:
                verified += 1

        avg_confidence = total_confidence / total

        return {
            "total": total,
            "by_type": types,
            "avg_confidence": avg_confidence,
            "verified_count": verified,
            "verification_rate": verified / total if total > 0 else 0,
            "health_status": "healthy" if avg_confidence > 0.6 and verified / total > 0.5 else "needs_attention",
            "timestamp": datetime.now().isoformat(),
        }
