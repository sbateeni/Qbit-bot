from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class BrokerCredentials:
    provider: str
    account_id: str
    api_key: str
    environment: str = "practice"


class BrokerAdapter(ABC):
    @abstractmethod
    def get_account(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        raise NotImplementedError

    @abstractmethod
    def open_market_order(
        self,
        symbol: str,
        side: str,
        units: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        client_tag: str = "Qbit",
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def close_position(self, instrument: str, side: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError
