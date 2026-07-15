"""
Environment Platform – Local Services provider (Weather, News, etc.)
"""

import os
import logging
import requests
from typing import Dict, Any, List, Optional

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalServicesProvider(EnvironmentProvider):
    """
    Local services provider for external APIs (weather, news, etc.)
    """

    def __init__(self, secure_memory=None):
        self.secure_memory = secure_memory
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info("[LocalServicesProvider] Initialized.")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalServicesProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_services",
            domain=Domain.SERVICES,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Local services for external APIs (weather, news).",
            capabilities=[
                EnvironmentProviderCapability(
                    name="weather",
                    description="Get current weather for a city.",
                    parameters={"city": {"type": "string", "description": "City name"}},
                    returns={"weather": {"type": "string"}}
                ),
                EnvironmentProviderCapability(
                    name="news",
                    description="Get latest news headlines for a topic.",
                    parameters={"topic": {"type": "string", "description": "Topic (e.g., technology)"}},
                    returns={"articles": {"type": "array"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["weather", "news"]

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}

        try:
            if capability == "weather":
                city = params.get('city') or params.get('location') or "London"
                url = f"https://wttr.in/{city}?format=%C+%t&lang=en"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return {"weather": response.text.strip()}
                else:
                    return {"error": f"HTTP {response.status_code}"}

            elif capability == "news":
                topic = params.get('topic', "technology")
                api_key = os.getenv("NEWS_API_KEY", "")
                if not api_key:
                    return {"error": "NEWS_API_KEY not set in environment variables"}
                url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={api_key}&pageSize=5&sortBy=publishedAt"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    headlines = []
                    for article in articles[:5]:
                        headlines.append({
                            "title": article.get("title"),
                            "source": article.get("source", {}).get("name"),
                            "url": article.get("url"),
                        })
                    return {"articles": headlines}
                else:
                    return {"error": f"News API error: {response.status_code}"}

            else:
                return {"error": f"Unknown capability: {capability}"}

        except Exception as e:
            logger.error(f"[LocalServicesProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
