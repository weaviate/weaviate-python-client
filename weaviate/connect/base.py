from abc import ABC, abstractmethod
from typing import Dict


class _ConnectionBase(ABC):
    @abstractmethod
    def get_current_bearer_token(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def _get_additional_headers(self) -> Dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def get_proxies(self) -> dict:
        raise NotImplementedError
