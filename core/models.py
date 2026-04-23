from pydantic import BaseModel, Field, validator
from typing import Optional
import MetaTrader5 as mt5

class TradeOrder(BaseModel):
    symbol: str = Field(..., min_length=1)
    order_type: str = Field(..., pattern="^(buy|sell|BUY|SELL)$")
    volume: float = Field(..., gt=0)
    sl: float = Field(..., ge=0)
    tp: float = Field(..., ge=0)
    magic: int = Field(default=123456)
    comment: str = Field(default="Qbit Trade")
    deviation: int = Field(default=20)

    @validator('order_type')
    def normalize_type(cls, v):
        return v.lower()

class PendingOrder(BaseModel):
    symbol: str = Field(..., min_length=1)
    order_type: int  # mt5 constant like mt5.ORDER_TYPE_BUY_LIMIT
    price: float = Field(..., gt=0)
    volume: float = Field(..., gt=0)
    sl: float = Field(..., ge=0)
    tp: float = Field(..., ge=0)
    magic: int = Field(default=123456)
    comment: str = Field(default="Qbit Pending")
    deviation: int = Field(default=20)
