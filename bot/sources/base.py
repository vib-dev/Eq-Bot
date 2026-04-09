from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Event


class SourceAdapter(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> list[Event]:
        raise NotImplementedError

