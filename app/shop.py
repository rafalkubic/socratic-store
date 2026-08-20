from __future__ import annotations

from decimal import Decimal
from functools import wraps
from uuid import uuid4

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from .extensions import db
from .models import Category, Order, OrderItem, PaymentTransaction, Product


shop_bp = Blueprint("shop", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.get("user"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def _cart() -> dict[str, int]:
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
    return cart


def _cart_lines():
    cart = _cart()
    ids = [int(k) for k, qty in cart.items() if str(k).isdigit() and int(qty) > 0]
    products = Product.query.filter(Product.id.in_(ids), Product.is_active.is_(True)).all() if ids else []
    by_id = {p.id: p for p in products}
    lines = []
    total = Decimal("0.00")
    for key, qty in cart.items():
        if not str(key).isdigit():
            continue
        product = by_id.get(int(key))
        if not product:
            continue
        quantity = max(1, min(int(qty), max(product.stock_qty, 1)))
        line_total = product.price_pln * quantity
        total += line_total
        lines.append({"product": product, "quantity": quantity, "line_total": line_total})
    return lines, total


@shop_bp.get("/")
def home():
    categories = Category.query.order_by(Category.sort_order, Category.id).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.id).all()
    return render_template("index.html", categories=categories, products=products)


@shop_bp.get("/category/<slug>")
def category(slug: str):
    category_obj = Category.query.filter_by(slug=slug).first_or_404()
    products = Product.query.filter_by(category_id=category_obj.id, is_active=True).order_by(Product.id).all()
    return render_template("category.html", category=category_obj, products=products)


@shop_bp.get("/product/<slug>")
def product(slug: str):
    product_obj = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template("product.html", product=product_obj)


@shop_bp.post("/cart/add/<int:product_id>")
def cart_add(product_id: int):
    product_obj = Product.query.filter_by(id=product_id, is_active=True).first_or_404()
    try:
        requested_qty = int(request.form.get("quantity", 1))
    except (TypeError, ValueError):
        requested_qty = 1
    qty = max(1, min(requested_qty, 20))
    cart = _cart()
    cart[str(product_id)] = min(int(cart.get(str(product_id), 0)) + qty, max(product_obj.stock_qty, 1))
    session["cart"] = cart
    session.modified = True
    return redirect(request.referrer or url_for("shop.cart"))


@shop_bp.post("/cart/remove/<int:product_id>")
def cart_remove(product_id: int):
    cart = _cart()
    cart.pop(str(product_id), None)
    session["cart"] = cart
    session.modified = True
    return redirect(url_for("shop.cart"))


@shop_bp.get("/cart")
def cart():
    lines, total = _cart_lines()
    return render_template("cart.html", lines=lines, total=total)


@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    lines, total = _cart_lines()
    if not lines:
        return redirect(url_for("shop.cart"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower() or g.user.email
        order = Order(
            public_id=str(uuid4()),
            user_id=g.user.id,
            email=email,
            total_amount=total,
            currency="PLN",
            status="payment_pending",
            payment_provider="przelewy24",
        )
        db.session.add(order)
        db.session.flush()
        for line in lines:
            product_obj = line["product"]
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product_obj.id,
                    sku=product_obj.sku,
                    name=product_obj.name_for(g.lang),
                    unit_price=product_obj.price_pln,
                    quantity=line["quantity"],
                    line_total=line["line_total"],
                )
            )

        payment = PaymentTransaction(
            order_id=order.id,
            provider="przelewy24",
            session_id=uuid4().hex,
            status="created",
        )
        db.session.add(payment)
        db.session.commit()
        return redirect(url_for("payments.start_payment", order_public_id=order.public_id))

    return render_template("checkout.html", lines=lines, total=total)


@shop_bp.get("/orders/<public_id>")
@login_required
def order_detail(public_id: str):
    order = Order.query.filter_by(public_id=public_id, user_id=g.user.id).first_or_404()
    return render_template("order.html", order=order)


@shop_bp.get("/lang/<lang>")
def set_language(lang: str):
    if lang in {"pl", "en"}:
        session["lang"] = lang
        if g.get("user"):
            g.user.preferred_language = lang
            db.session.commit()
    return redirect(request.referrer or url_for("shop.home"))
