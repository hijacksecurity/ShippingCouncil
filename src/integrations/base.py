"""Base integration interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseIntegration(ABC):
    """Abstract base class for all integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the integration name."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the service."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the service."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the integration is healthy."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
