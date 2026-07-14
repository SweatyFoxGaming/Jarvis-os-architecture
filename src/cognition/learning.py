import logging
from typing import List, Optional
from datetime import datetime

from src.cognition.models import Belief, KnowledgeItem, KnowledgeType, KnowledgeVerificationStatus, Experience
from src.cognition.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Converts Beliefs into Knowledge, and updates existing Knowledge.
    """

    def __init__(self, knowledge_store: KnowledgeStore):
        self.knowledge_store = knowledge_store
        logger.info("[LearningEngine] Initialized.")

    def learn_from_beliefs(self, beliefs: List[Belief], source_experience: Optional[Experience] = None) -> int:
        """
        Process a list of beliefs and update the Knowledge Store.
        Returns the number of new Knowledge items created.
        """
        count = 0
        for belief in beliefs:
            if belief.confidence >= 0.8:
                # Promote to Knowledge
                knowledge = self._belief_to_knowledge(belief, source_experience)
                self.knowledge_store.store(knowledge)
                count += 1
                logger.info(f"[LearningEngine] Promoted belief to knowledge: {knowledge.content[:100]}...")
            elif belief.confidence >= 0.5:
                # Store as a belief for later reinforcement
                # In a full implementation, we'd have a BeliefStore.
                # For now, we'll store it as Knowledge with lower confidence.
                knowledge = self._belief_to_knowledge(belief, source_experience)
                knowledge.confidence = belief.confidence
                knowledge.verification_status = KnowledgeVerificationStatus.UNVERIFIED
                self.knowledge_store.store(knowledge)
                count += 1
                logger.info(f"[LearningEngine] Stored low-confidence belief as knowledge: {knowledge.content[:100]}...")
            else:
                logger.debug(f"[LearningEngine] Belief confidence too low: {belief.confidence}")
        return count

    def _belief_to_knowledge(self, belief: Belief, source_experience: Optional[Experience] = None) -> KnowledgeItem:
        """
        Convert a Belief to a KnowledgeItem.
        """
        # Determine knowledge type based on claim content (simplified)
        knowledge_type = KnowledgeType.FACT
        claim_lower = belief.claim.lower()
        if "should" in claim_lower or "prefer" in claim_lower:
            knowledge_type = KnowledgeType.PREFERENCE
        elif "how to" in claim_lower or "procedure" in claim_lower:
            knowledge_type = KnowledgeType.PROCEDURE
        elif "relationship" in claim_lower:
            knowledge_type = KnowledgeType.RELATIONSHIP

        evidence = [belief.uuid]
        if source_experience:
            evidence.append(source_experience.uuid)

        return KnowledgeItem(
            type=knowledge_type,
            content=belief.claim,
            confidence=belief.confidence,
            evidence=evidence,
            verification_status=KnowledgeVerificationStatus.VERIFIED_BY_LLM if belief.confidence >= 0.8 else KnowledgeVerificationStatus.UNVERIFIED,
            source=belief.source,
            source_uuid=belief.source_uuid,
            reinforcement_count=belief.reinforcement_count,
        )
