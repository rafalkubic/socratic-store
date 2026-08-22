from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(160), nullable=True)
    preferred_language = db.Column(db.String(2), nullable=False, default="pl")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    oauth_accounts = db.relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )
    orders = db.relationship("Order", back_populates="user")
    dialogue_profile = db.relationship(
        "UserDialogueProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    profile_observations = db.relationship(
        "UserProfileObservation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)


class OAuthAccount(db.Model):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        db.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = db.Column(db.String(32), nullable=False)
    provider_user_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="oauth_accounts")


class UserDialogueProfile(db.Model):
    """Persisted dialogue-orientation weights; not a diagnosis or belief record."""

    __tablename__ = "user_dialogue_profiles"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    hylik_weight = db.Column(db.Numeric(8, 6), nullable=False, default=Decimal("0.333333"))
    psychik_weight = db.Column(db.Numeric(8, 6), nullable=False, default=Decimal("0.333333"))
    pneumatyk_weight = db.Column(db.Numeric(8, 6), nullable=False, default=Decimal("0.333334"))
    dominant_profile = db.Column(db.String(16), nullable=False, default="neutral")
    confidence = db.Column(db.Numeric(8, 6), nullable=False, default=Decimal("0.000000"))
    sample_count = db.Column(db.Integer, nullable=False, default=0)
    profiling_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_conversation_id = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = db.relationship("User", back_populates="dialogue_profile")


class UserProfileObservation(db.Model):
    """Coarse numeric evidence only. Raw prompts/messages are intentionally absent."""

    __tablename__ = "user_profile_observations"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id = db.Column(db.String(128), nullable=True, index=True)
    sample_number = db.Column(db.Integer, nullable=False)
    hylik_evidence = db.Column(db.Numeric(8, 6), nullable=False)
    psychik_evidence = db.Column(db.Numeric(8, 6), nullable=False)
    pneumatyk_evidence = db.Column(db.Numeric(8, 6), nullable=False)
    evidence_strength = db.Column(db.Numeric(8, 6), nullable=False)
    resulting_dominant_profile = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="profile_observations")


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name_pl = db.Column(db.String(120), nullable=False)
    name_en = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    products = db.relationship("Product", back_populates="category")

    def name_for(self, lang: str) -> str:
        return self.name_en if lang == "en" else self.name_pl


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name_pl = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200), nullable=False)
    description_pl = db.Column(db.Text, nullable=False)
    description_en = db.Column(db.Text, nullable=False)
    price_pln = db.Column(db.Numeric(10, 2), nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    image_path = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    category = db.relationship("Category", back_populates="products")

    def name_for(self, lang: str) -> str:
        return self.name_en if lang == "en" else self.name_pl

    def description_for(self, lang: str) -> str:
        return self.description_en if lang == "en" else self.description_pl


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="payment_pending", index=True)
    currency = db.Column(db.String(3), nullable=False, default="PLN")
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    payment_provider = db.Column(db.String(40), nullable=False, default="przelewy24")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = db.relationship("PaymentTransaction", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    sku = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")


class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = db.Column(db.String(40), nullable=False)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    provider_order_id = db.Column(db.String(100), nullable=True, index=True)
    token = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="created", index=True)
    raw_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = db.relationship("Order", back_populates="payments")
