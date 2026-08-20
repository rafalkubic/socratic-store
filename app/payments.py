from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal

import requests
from flask import Blueprint, current_app, flash, g, jsonify, redirect, request, session, url_for

from .extensions import csrf, db
from .models import Order, PaymentTransaction


payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


class P24Error(RuntimeError):
    pass


class P24Client:
    def __init__(self):
        self.merchant_id = int(current_app.config["P24_MERCHANT_ID"])
        self.pos_id = int(current_app.config["P24_POS_ID"])
        self.api_key = current_app.config["P24_API_KEY"]
        self.crc = current_app.config["P24_CRC"]
        sandbox = current_app.config["P24_SANDBOX"]
        host = "https://sandbox.przelewy24.pl" if sandbox else "https://secure.przelewy24.pl"
        self.api_base = f"{host}/api/v1"
        self.gateway_base = host

    @staticmethod
    def _sha384(payload: dict) -> str:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha384(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _amount_grosz(amount: Decimal) -> int:
        return int((amount * 100).quantize(Decimal("1")))

    def register(self, order: Order, payment: PaymentTransaction, lang: str) -> str:
        amount = self._amount_grosz(order.total_amount)
        sign = self._sha384(
            {
                "sessionId": payment.session_id,
                "merchantId": self.merchant_id,
                "amount": amount,
                "currency": order.currency,
                "crc": self.crc,
            }
        )
        body = {
            "merchantId": self.merchant_id,
            "posId": self.pos_id,
            "sessionId": payment.session_id,
            "amount": amount,
            "currency": order.currency,
            "description": f"Socratic Store — {order.public_id[:8]}",
            "email": order.email,
            "country": "PL",
            "language": "en" if lang == "en" else "pl",
            "urlReturn": f"{current_app.config['APP_BASE_URL']}{url_for('shop.order_detail', public_id=order.public_id)}",
            "urlStatus": f"{current_app.config['APP_BASE_URL']}{url_for('payments.p24_status')}",
            "sign": sign,
        }
        response = requests.post(
            f"{self.api_base}/transaction/register",
            json=body,
            auth=(str(self.pos_id), self.api_key),
            timeout=20,
        )
        payment.raw_response = response.text[:10000]
        if not response.ok:
            raise P24Error(f"P24 register HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        token = (data.get("data") or {}).get("token")
        if not token:
            raise P24Error(f"P24 register did not return token: {data}")
        payment.token = token
        payment.status = "registered"
        db.session.commit()
        return f"{self.gateway_base}/trnRequest/{token}"

    def validate_notification_sign(self, payload: dict) -> bool:
        required = [
            "merchantId",
            "posId",
            "sessionId",
            "amount",
            "originAmount",
            "currency",
            "orderId",
            "methodId",
            "statement",
        ]
        if any(key not in payload for key in required) or "sign" not in payload:
            return False
        sign_payload = {key: payload[key] for key in required}
        sign_payload["crc"] = self.crc
        expected = self._sha384(sign_payload)
        return expected == str(payload["sign"])

    def verify(self, payment: PaymentTransaction, order: Order, provider_order_id: int) -> dict:
        amount = self._amount_grosz(order.total_amount)
        sign = self._sha384(
            {
                "sessionId": payment.session_id,
                "orderId": provider_order_id,
                "amount": amount,
                "currency": order.currency,
                "crc": self.crc,
            }
        )
        body = {
            "merchantId": self.merchant_id,
            "posId": self.pos_id,
            "sessionId": payment.session_id,
            "amount": amount,
            "currency": order.currency,
            "orderId": provider_order_id,
            "sign": sign,
        }
        response = requests.put(
            f"{self.api_base}/transaction/verify",
            json=body,
            auth=(str(self.pos_id), self.api_key),
            timeout=20,
        )
        if not response.ok:
            raise P24Error(f"P24 verify HTTP {response.status_code}: {response.text[:500]}")
        return response.json()



def _mark_order_paid(order: Order, payment: PaymentTransaction | None, provider_order_id: str, payment_status: str) -> None:
    if order.status != "paid":
        for item in order.items:
            if item.product is not None:
                item.product.stock_qty = max(0, item.product.stock_qty - item.quantity)
        order.status = "paid"
        order.paid_at = datetime.utcnow()
    if payment:
        payment.provider_order_id = provider_order_id
        payment.status = payment_status


def _p24_is_configured() -> bool:
    keys = ["P24_MERCHANT_ID", "P24_POS_ID", "P24_API_KEY", "P24_CRC"]
    return current_app.config.get("P24_ENABLED") and all(current_app.config.get(k) for k in keys)


@payments_bp.get("/start/<order_public_id>")
def start_payment(order_public_id: str):
    if not g.get("user"):
        return redirect(url_for("auth.login"))
    order = Order.query.filter_by(public_id=order_public_id, user_id=g.user.id).first_or_404()
    payment = (
        PaymentTransaction.query.filter_by(order_id=order.id, provider="przelewy24")
        .order_by(PaymentTransaction.id.desc())
        .first()
    )
    if not payment:
        return redirect(url_for("shop.order_detail", public_id=order.public_id))

    if _p24_is_configured():
        try:
            client = P24Client()
            if payment.token:
                target = f"{client.gateway_base}/trnRequest/{payment.token}"
            else:
                target = client.register(order, payment, g.get("lang", "pl"))
            # Cart is cleared after successful P24 registration; payment confirmation happens by webhook.
            session["cart"] = {}
            return redirect(target)
        except Exception as exc:
            current_app.logger.exception("P24 registration failed")
            payment.status = "error"
            payment.raw_response = str(exc)[:10000]
            db.session.commit()
            flash(f"Błąd inicjalizacji płatności: {exc}", "error")
            return redirect(url_for("shop.order_detail", public_id=order.public_id))

    flash("Płatności P24 nie są skonfigurowane. W trybie DEV możesz użyć symulacji.", "error")
    return redirect(url_for("shop.order_detail", public_id=order.public_id))


@payments_bp.post("/demo/<order_public_id>")
def demo_payment(order_public_id: str):
    if not current_app.config.get("DEMO_PAYMENT_MODE"):
        return jsonify({"error": "disabled"}), 404
    if not g.get("user"):
        return redirect(url_for("auth.login"))
    order = Order.query.filter_by(public_id=order_public_id, user_id=g.user.id).first_or_404()
    payment = PaymentTransaction.query.filter_by(order_id=order.id).order_by(PaymentTransaction.id.desc()).first()
    _mark_order_paid(order, payment, provider_order_id="DEMO", payment_status="paid_demo")
    db.session.commit()
    session["cart"] = {}
    flash("Płatność została zasymulowana — tryb developerski.", "success")
    return redirect(url_for("shop.order_detail", public_id=order.public_id))


@payments_bp.post("/p24/status")
@csrf.exempt
def p24_status():
    if not _p24_is_configured():
        return jsonify({"error": "P24 disabled"}), 503

    payload = request.get_json(silent=True) or request.form.to_dict()
    client = P24Client()
    if not client.validate_notification_sign(payload):
        return jsonify({"error": "invalid sign"}), 400

    payment = PaymentTransaction.query.filter_by(session_id=str(payload.get("sessionId"))).first()
    if not payment:
        return jsonify({"error": "unknown session"}), 404
    order = payment.order

    expected_amount = int(order.total_amount * 100)
    if int(payload.get("amount", -1)) != expected_amount or payload.get("currency") != order.currency:
        return jsonify({"error": "amount/currency mismatch"}), 400

    provider_order_id = int(payload["orderId"])
    try:
        client.verify(payment, order, provider_order_id)
    except P24Error as exc:
        current_app.logger.exception("P24 verification failed")
        payment.status = "verification_failed"
        payment.raw_response = str(exc)[:10000]
        db.session.commit()
        return jsonify({"error": "verification failed"}), 400

    payment.raw_response = json.dumps(payload, ensure_ascii=False)[:10000]
    _mark_order_paid(order, payment, provider_order_id=str(provider_order_id), payment_status="paid")
    db.session.commit()
    return jsonify({"ok": True})
