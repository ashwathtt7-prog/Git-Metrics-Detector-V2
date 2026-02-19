from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderConfig:
    name: str
    max_context_tokens: int
    supports_json_mode: bool
    rpm_limit: Optional[int] = None
    rpd_limit: Optional[int] = None


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def config(self) -> ProviderConfig: ...

    @abc.abstractmethod
    async def generate(self, prompt: str, temperature: float = 0.1) -> str: ...

    @abc.abstractmethod
    def is_available(self) -> bool: ...
