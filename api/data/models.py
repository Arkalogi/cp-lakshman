from sqlalchemy import (
    Enum,
    Float,
    Column,
    Integer,
    String,
    Text,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from api.commons.enums import OrderSide, OrderStatus


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    demat_apis = relationship(
        "DematApi", back_populates="user", foreign_keys="DematApi.user_id"
    )
    strategies = relationship(
        "Strategy", back_populates="user", foreign_keys="Strategy.user_id"
    )


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    description = Column(Text)
    config = Column(JSON)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="strategies", foreign_keys=[user_id])

    subscriptions = relationship(
        "StrategySubscription",
        back_populates="subscriber",
        foreign_keys="StrategySubscription.subscriber_id",
    )
    followers = relationship(
        "StrategySubscription",
        back_populates="target",
        foreign_keys="StrategySubscription.target_id",
    )


class DematApi(Base):
    __tablename__ = "demat_apis"

    id = Column(Integer, primary_key=True)
    config = Column(JSON)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="demat_apis", foreign_keys=[user_id])

    subscriptions = relationship(
        "DematApiSubscription",
        back_populates="subscriber",
        foreign_keys="DematApiSubscription.subscriber_id",
    )
    followers = relationship(
        "DematApiSubscription",
        back_populates="target",
        foreign_keys="DematApiSubscription.target_id",
    )

    orders = relationship("Order", back_populates="api")


class DematApiSubscription(Base):
    __tablename__ = "demat_api_subscriptions"

    id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, ForeignKey("demat_apis.id", ondelete="CASCADE"))
    target_id = Column(Integer, ForeignKey("demat_apis.id", ondelete="CASCADE"))
    multiplier = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=True)

    subscriber = relationship(
        "DematApi", back_populates="subscriptions", foreign_keys=[subscriber_id]
    )
    target = relationship(
        "DematApi", back_populates="followers", foreign_keys=[target_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "subscriber_id", "target_id", name="uq_demat_api_subscription"
        ),
    )


class StrategySubscription(Base):
    __tablename__ = "strategy_subscriptions"

    id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"))
    target_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"))

    subscriber = relationship(
        "Strategy", back_populates="subscriptions", foreign_keys=[subscriber_id]
    )
    target = relationship(
        "Strategy", back_populates="followers", foreign_keys=[target_id]
    )

    __table_args__ = (
        UniqueConstraint("subscriber_id", "target_id", name="uq_strategy_subscription"),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    tag = Column(String(20), index=True)
    instrument_token = Column(String(12), nullable=False)
    trading_symbol = Column(String(50), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), nullable=False, default=OrderStatus.PENDING.value)
    broker_order_id = Column(Text, nullable=True)
    filled_quantity = Column(Integer, default=0)
    average_price = Column(Float, default=0)
    error_code = Column(String(5), nullable=True)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(Text, nullable=True)

    api_id = Column(
        Integer, ForeignKey("demat_apis.id", ondelete="SET NULL"), nullable=True
    )
    api = relationship("DematApi", back_populates="orders")
