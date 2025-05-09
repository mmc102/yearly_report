from abc import ABC
from pydantic import BaseModel
from app.schemas.no_code import NoCodeTransaction
from app.models.effect import EventType


class Event(ABC, BaseModel):
    type: EventType


class NewTransactionsEvent(Event):
    type: EventType = EventType.NEW_TRANSACTION
    transactions: list[NoCodeTransaction]
    account_name: str
    count: int


class NewAccountLinkedEvent(Event):
    type: EventType = EventType.NEW_ACCOUNT_LINKED
    account_name: str
