from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_email = Column(String, unique=True)
    api_key = Column(String, unique=True)
    active = Column(Boolean, default=True)
    subscriptions = relationship("BillingSubscription", back_populates="api_key_rel")


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"
    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)
    stripe_customer_id = Column(String, index=True)
    stripe_subscription_id = Column(String, unique=True, index=True)
    stripe_price_id = Column(String)
    plan_name = Column(String, default="free")
    status = Column(String, default="inactive", index=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    api_key_rel = relationship("APIKey", back_populates="subscriptions")


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"
    id = Column(Integer, primary_key=True)
    stripe_event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
