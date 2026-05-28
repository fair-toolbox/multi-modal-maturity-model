from abc import ABC, abstractmethod
from typing import Any


class BaseClient(ABC):
    @abstractmethod
    async def fetch(self) -> dict[str, Any]:
        pass
