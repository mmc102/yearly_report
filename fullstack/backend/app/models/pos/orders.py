from decimal import Decimal
from typing import NewType
from datetime import datetime
from app.models.models import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import UserId
from app.models.pos.shop import ShopId


OrderId = NewType("OrderId", int)
GuestOrdererId = NewType("GuestOrdererId", int)
OrderItemId = NewType("OrderItemId", int)
OrderableId = NewType("OrderableId", int)


class GuestOrderer(Base):
    __tablename__ = "guest_orderer"
    id: Mapped[GuestOrdererId] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Order(Base):
    __tablename__ = "order"

    id: Mapped[OrderId] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    placed_by: Mapped[GuestOrdererId | None] = mapped_column(
        ForeignKey("guest_orderer.id"), nullable=True
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("user.id"), nullable=False)
    shop_id: Mapped[ShopId] = mapped_column(ForeignKey("shop.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pickup_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OrderItem(Base):
    __tablename__ = "order_item"

    id: Mapped[OrderItemId] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    order_id: Mapped[OrderId] = mapped_column(ForeignKey("order.id"), nullable=False)
    orderable_id: Mapped[OrderableId] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[UserId] = mapped_column(ForeignKey("user.id"), nullable=False)


class Orderable(Base):
    __tablename__ = "orderable"

    id: Mapped[OrderableId] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    user_id: Mapped[UserId] = mapped_column(ForeignKey("user.id"), nullable=False)
