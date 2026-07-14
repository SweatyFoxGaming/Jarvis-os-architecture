import logging
import asyncio
from typing import Optional
from datetime import datetime

from src.cognition.reflection import ReflectionEngine
from src.cognition.learning import LearningEngine
from src.cognition.health import CognitiveHealthMonitor
from src.cognition.workspace import CognitiveWorkspace
from src.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class SleepScheduler:
    """
    Background process that runs deep reflection, learning, and health checks.
    """

    def __init__(
        self,
        reflection_engine: ReflectionEngine,
        learning_engine: LearningEngine,
        health_monitor: CognitiveHealthMonitor,
        workspace: CognitiveWorkspace,
        interval_seconds: int = 3600 * 12,  # 12 hours
    ):
        self.reflection = reflection_engine
        self.learning = learning_engine
        self.health = health_monitor
        self.workspace = workspace
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        logger.info(f"[SleepScheduler] Initialized with interval {interval_seconds}s")

    async def start(self) -> None:
        """Start the background sleep cycle."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("[SleepScheduler] Started.")

    async def _run(self) -> None:
        """Main loop."""
        while self._running:
            await asyncio.sleep(self.interval)
            try:
                await self._sleep_cycle()
            except Exception as e:
                logger.error(f"[SleepScheduler] Sleep cycle failed: {e}", exc_info=True)

    async def _sleep_cycle(self) -> None:
        """Perform one sleep cycle."""
        logger.info("[SleepScheduler] Starting sleep cycle...")
        # Deep reflection on all recent experiences? This is complex.
        # For now, we'll just run health check and log.
        # A full implementation would retrieve recent experiences and run deep reflection.
        metrics = self.health.get_metrics()
        logger.info(f"[SleepScheduler] Health metrics: {metrics}")
        # We would also run reflection on a batch of experiences.
        # For now, we just log.
        logger.info("[SleepScheduler] Sleep cycle complete.")

    async def stop(self) -> None:
        """Stop the sleep cycle."""
        if self._task:
            self._running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[SleepScheduler] Stopped.")
