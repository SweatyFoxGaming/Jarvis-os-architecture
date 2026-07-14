import logging
import os
import json
from typing import List, Optional, Dict, Any

import requests  # <-- Make sure requests is installed in the container

from src.capabilities.providers.base import CapabilityProvider
from src.capabilities.manifest import (
    CapabilityManifest, CapabilityIdentity, CapabilityClassification,
    CapabilityRequirements, CapabilityExecution, CapabilityResources,
    CapabilityLifecycle, CapabilityMetadata, CapabilityHealth
)
from src.capabilities.contract import Capability
from src.capabilities.context import ExecutionContext

logger = logging.getLogger(__name__)


# ============================================================================
# BUILT-IN CAPABILITY IMPLEMENTATIONS
# ============================================================================

def _brave_search(objective: str) -> str:
    """
    Perform a web search using the Brave Search API.
    Returns a formatted summary of the top results.
    """
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return "Error: BRAVE_API_KEY environment variable is not set. Please add it to your .env file."

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": objective,
        "count": 5  # Top 5 results are enough for a summary
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get("web", {}).get("results", [])
        if not results:
            return f"No results found for '{objective}'."

        # Build a clean, readable summary
        summary = f"**Top results for '{objective}':**\n\n"
        for i, item in enumerate(results[:5], 1):
            title = item.get("title", "Untitled")
            snippet = item.get("snippet", "No description available.")
            url = item.get("url", "#")
            summary += f"{i}. **{title}**\n   {snippet}\n   Source: {url}\n\n"

        return summary.strip()

    except requests.exceptions.Timeout:
        logger.error("Brave API request timed out after 10 seconds.")
        return "The search request timed out. Please try again in a moment."
    except requests.exceptions.RequestException as e:
        logger.error(f"Brave API request failed: {e}")
        return f"Sorry, I couldn't complete the search due to a network error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during Brave search: {e}")
        return f"An unexpected error occurred while searching: {str(e)}"


# ============================================================================
# CAPABILITY PROVIDER
# ============================================================================

class BuiltinProvider(CapabilityProvider):
    """
    Provides the built‑in capabilities that are hardcoded in Jarvis.
    For now, we return manifests and implementations from the existing v2_main.
    """

    def __init__(self, tool_registry=None, engine=None):
        self.tool_registry = tool_registry
        self.engine = engine
        self._manifests: List[CapabilityManifest] = []
        self._implementations: Dict[str, Capability] = {}

    def _create_wrapper(self, name: str, description: str, handler) -> Capability:
        """
        Create a wrapper that implements the Capability contract.
        """
        class WrappedCapability(Capability):
            def initialize(self) -> None:
                pass

            def validate(self, context: ExecutionContext) -> bool:
                return True

            def execute(self, context: ExecutionContext) -> Dict[str, Any]:
                # Call the handler with the parameters
                # For simplicity, we assume the handler expects a dict
                # In the future, we'll map from context to handler args
                params = context.extra.get("params", {})
                result = handler(**params) if callable(handler) else handler
                return {"result": result}

            def health(self) -> Dict[str, Any]:
                return {"status": CapabilityHealth.HEALTHY}

            def shutdown(self) -> None:
                pass

            def metadata(self) -> Dict[str, Any]:
                return {"name": name, "description": description}

        return WrappedCapability()

    def discover(self) -> List[CapabilityManifest]:
        # In a real implementation, we'd scan the registry.
        # For now, we return a default set (hardcoded).
        default_manifests = [
            CapabilityManifest(
                identity=CapabilityIdentity(id="research_specialist", name="Research Specialist", description="Perform deep factual research using Brave Search."),
                classification=CapabilityClassification(category="reasoning", tags=["research", "facts", "web"]),
                requirements=CapabilityRequirements(permissions=["network"], dependencies=[]),
                execution=CapabilityExecution(entrypoint="", timeout=60),
                resources=CapabilityResources(estimated_tokens=500, estimated_memory_mb=128, estimated_duration_sec=10),
                lifecycle=CapabilityLifecycle(version="1.0.0"),
                metadata=CapabilityMetadata(author="Jarvis Core Team", source="built-in")
            ),
            # Add others similarly...
        ]
        self._manifests = default_manifests
        return self._manifests

    def load(self, manifest: CapabilityManifest) -> Optional[Capability]:
        # Find the corresponding handler from the tool registry
        # For now, we hardcode a mapping
        handler_map = {
            "research_specialist": _brave_search,  # <-- REAL IMPLEMENTATION
            # Add other handlers here as we build them
        }
        handler = handler_map.get(manifest.identity.id)
        if handler is None:
            logger.warning(f"No handler found for {manifest.identity.id}")
            return None
        wrapper = self._create_wrapper(manifest.identity.id, manifest.identity.description, handler)
        return wrapper

    def watch(self) -> None:
        # No‑op for built‑in
        pass
