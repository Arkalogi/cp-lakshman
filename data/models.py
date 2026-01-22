from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


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

    apis = relationship(
        "Subscription",
        back_populates="subscriber",
        foreign_keys="Subscription.subscriber_id",
    )
    strategies = relationship(
        "Strategy", back_populates="target", foreign_keys="Subscription.target_id"
    )


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    description = Column(Text)
    config = Column(Text)

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
    config = Column(Text)

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


class DematApiSubscription(Base):
    __tablename__ = "demat_api_subscriptions"

    id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, ForeignKey("demat_apis.id", ondelete="CASCADE"))
    target_id = Column(Integer, ForeignKey("demat_apis.id", ondelete="CASCADE"))

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
