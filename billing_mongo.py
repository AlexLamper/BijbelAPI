"""
MongoDB persistence for API keys, Stripe subscriptions, and webhook idempotency.
Connection: set MONGODB_URI (full SRV string). Legacy fallback: MONGO_URI.
Optional MONGODB_DB_NAME (default: bijbelapi).
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Optional

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from bson import ObjectId

_client: Optional[MongoClient] = None
_indexes_ensured = False


def get_mongo_uri() -> str:
    primary = os.getenv("MONGODB_URI", "").strip()
    if primary:
        return primary
    # Backward-compatibility: some deployments still use MONGO_URI.
    return os.getenv("MONGO_URI", "").strip()


def get_mongo_uri_source() -> str:
    if os.getenv("MONGODB_URI", "").strip():
        return "MONGODB_URI"
    if os.getenv("MONGO_URI", "").strip():
        return "MONGO_URI"
    return ""


def mongo_config_error() -> Optional[str]:
    uri = get_mongo_uri()
    if not uri:
        return "MongoDB URI ontbreekt: zet MONGODB_URI (of legacy MONGO_URI) met een mongodb:// of mongodb+srv:// connection string."
    if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        source = get_mongo_uri_source() or "MONGODB_URI"
        return (
            f"{source} is ongeldig: URI moet beginnen met 'mongodb://' of 'mongodb+srv://'. "
            "Gebruik hier geen https:// website-URL."
        )
    return None


def get_mongo_db_name() -> str:
    return os.getenv("MONGODB_DB_NAME", "bijbelapi").strip() or "bijbelapi"


def get_mongo_client() -> MongoClient:
    global _client
    err = mongo_config_error()
    if err:
        raise RuntimeError(err)
    uri = get_mongo_uri()
    if _client is None:
        _client = MongoClient(uri, serverSelectionTimeoutMS=12000)
    return _client


def get_billing_db():
    return get_mongo_client()[get_mongo_db_name()]


def ensure_billing_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return
    db = get_billing_db()
    db.api_keys.create_index("user_email", unique=True)
    db.api_keys.create_index("api_key", unique=True)
    db.billing_subscriptions.create_index("stripe_subscription_id", unique=True, sparse=True)
    db.billing_subscriptions.create_index([("api_key_id", ASCENDING), ("updated_at", ASCENDING)])
    db.stripe_webhook_events.create_index("stripe_event_id", unique=True)
    _indexes_ensured = True


def ping_mongo() -> dict[str, Any]:
    t0 = time.perf_counter()
    db_name = get_mongo_db_name()
    config_error = mongo_config_error()
    if config_error:
        return {
            "ok": False,
            "error": config_error,
            "database": db_name,
            "source": get_mongo_uri_source() or None,
        }
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": True,
            "database": db_name,
            "ping_ms": ms,
            "message": "MongoDB bereikbaar",
        }
    except PyMongoError as e:
        return {"ok": False, "database": db_name, "error": str(e)[:500]}


def mongo_find_active_api_key_by_secret(db, secret: str) -> Optional[dict]:
    return db.api_keys.find_one({"api_key": secret, "active": True})


def mongo_find_api_key_by_secret(db, secret: str) -> Optional[dict]:
    return db.api_keys.find_one({"api_key": secret})


def mongo_find_api_key_by_email(db, email: str) -> Optional[dict]:
    return db.api_keys.find_one({"user_email": email})


def mongo_insert_api_key(db, email: str, key_str: str, active: bool = True) -> dict:
    now = datetime.utcnow()
    doc = {"user_email": email, "api_key": key_str, "active": active, "created_at": now}
    r = db.api_keys.insert_one(doc)
    doc["_id"] = r.inserted_id
    return doc


def mongo_set_api_key_active_by_email(db, email: str, active: bool) -> None:
    db.api_keys.update_one({"user_email": email}, {"$set": {"active": active}})


def mongo_set_api_key_active_by_id(db, oid: ObjectId, active: bool) -> None:
    db.api_keys.update_one({"_id": oid}, {"$set": {"active": active}})


def mongo_find_latest_subscription_by_api_key_id(db, api_key_oid: ObjectId) -> Optional[dict]:
    return db.billing_subscriptions.find_one(
        {"api_key_id": api_key_oid},
        sort=[("updated_at", -1)],
    )


def mongo_find_subscription_by_stripe_sub_id(db, stripe_sub_id: str) -> Optional[dict]:
    return db.billing_subscriptions.find_one({"stripe_subscription_id": stripe_sub_id})


def mongo_find_api_key_by_id(db, oid: ObjectId) -> Optional[dict]:
    return db.api_keys.find_one({"_id": oid})


def mongo_upsert_subscription_after_checkout(
    db,
    api_key_oid: ObjectId,
    stripe_customer_id: Any,
    stripe_subscription_id: Any,
    stripe_price_id: Any,
    plan_name: str,
) -> None:
    now = datetime.utcnow()
    existing = mongo_find_latest_subscription_by_api_key_id(db, api_key_oid)
    fields: dict[str, Any] = {
        "plan_name": plan_name,
        "status": "active",
        "updated_at": now,
    }
    if stripe_customer_id:
        fields["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id:
        fields["stripe_subscription_id"] = stripe_subscription_id
    if stripe_price_id:
        fields["stripe_price_id"] = stripe_price_id

    if not existing:
        insert_doc: dict[str, Any] = {
            "api_key_id": api_key_oid,
            "plan_name": plan_name,
            "status": "active",
            "current_period_end": None,
            "created_at": now,
            "updated_at": now,
        }
        if stripe_customer_id:
            insert_doc["stripe_customer_id"] = stripe_customer_id
        if stripe_subscription_id:
            insert_doc["stripe_subscription_id"] = stripe_subscription_id
        if stripe_price_id:
            insert_doc["stripe_price_id"] = stripe_price_id
        db.billing_subscriptions.insert_one(insert_doc)
        return

    merged = {**fields}
    for k in ("stripe_customer_id", "stripe_subscription_id", "stripe_price_id"):
        if k not in merged and existing.get(k):
            merged[k] = existing[k]
    db.billing_subscriptions.update_one({"_id": existing["_id"]}, {"$set": merged})


def mongo_subscription_set_status(
    db,
    stripe_subscription_id: str,
    status: str,
) -> Optional[dict]:
    sub = mongo_find_subscription_by_stripe_sub_id(db, stripe_subscription_id)
    if not sub:
        return None
    db.billing_subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
    )
    sub["status"] = status
    return sub


def mongo_record_webhook_event(db, event_id: str, event_type: str) -> bool:
    """Return True if this event_id was already recorded (duplicate)."""
    try:
        db.stripe_webhook_events.insert_one(
            {
                "stripe_event_id": event_id,
                "event_type": event_type,
                "processed_at": datetime.utcnow(),
            }
        )
        return False
    except DuplicateKeyError:
        return True
