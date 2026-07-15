from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from src.environment.models import ProviderHealth, ProviderMetadata, Domain


class EnvironmentProvider(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass

    @abstractmethod
    def health(self) -> ProviderHealth:
        pass

    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass

    @abstractmethod
    def capabilities(self) -> List[str]:
        pass

    @abstractmethod
    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
