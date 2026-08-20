from __future__ import annotations

import re

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from .extensions import db, oauth
from .models import OAuthAccount, User
from .translations import translate


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _t(key: str) -> str:
    return translate(g.get("lang", "pl"), key)


def _safe_username(seed: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_.-]+", "-", seed.strip().lower()).strip("-._") or "user"
    base = base[:70]
    candidate = base
    i = 1
    while User.query.filter_by(username=candidate).first():
        i += 1
        candidate = f"{base[:70-len(str(i))-1]}-{i}"
    return candidate


def _login_user(user: User) -> None:
    cart = session.get("cart", {})
    lang = session.get("lang") or user.preferred_language or "pl"
    session.clear()
    session["user_id"] = user.id
    session["lang"] = lang
    session["cart"] = cart


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_repeat = request.form.get("password_repeat", "")

        if not email or "@" not in email or not username:
            flash("Uzupełnij poprawnie e-mail i nazwę użytkownika.", "error")
            return render_template("register.html")
        if password != password_repeat:
            flash(_t("password_mismatch"), "error")
            return render_template("register.html")
        if len(password) < 8:
            flash(_t("password_short"), "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash(_t("email_exists"), "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash(_t("username_exists"), "error")
            return render_template("register.html")

        user = User(email=email, username=username, display_name=username, preferred_language=g.lang)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        _login_user(user)
        flash(_t("account_created"), "success")
        return redirect(url_for("shop.home"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(or_(User.email == identifier.lower(), User.username == identifier)).first()
        if not user or not user.check_password(password):
            flash(_t("invalid_credentials"), "error")
            return render_template("login.html")
        _login_user(user)
        return redirect(url_for("shop.home"))
    return render_template("login.html")


@auth_bp.post("/logout")
def logout():
    lang = session.get("lang", "pl")
    session.clear()
    session["lang"] = lang
    return redirect(url_for("shop.home"))


@auth_bp.get("/oauth/<provider>")
def oauth_login(provider: str):
    if provider not in {"google", "facebook"}:
        return redirect(url_for("auth.login"))

    if provider == "google":
        if not current_app.config.get("GOOGLE_CLIENT_ID") or not current_app.config.get("GOOGLE_CLIENT_SECRET"):
            flash(_t("oauth_not_configured"), "error")
            return redirect(url_for("auth.login"))
        client = oauth.google
    else:
        if not current_app.config.get("FACEBOOK_CLIENT_ID") or not current_app.config.get("FACEBOOK_CLIENT_SECRET"):
            flash(_t("oauth_not_configured"), "error")
            return redirect(url_for("auth.login"))
        client = oauth.facebook

    redirect_uri = url_for("auth.oauth_callback", provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


@auth_bp.get("/oauth/<provider>/callback")
def oauth_callback(provider: str):
    if provider == "google":
        client = oauth.google
        token = client.authorize_access_token()
        info = token.get("userinfo") or client.get("userinfo").json()
        provider_user_id = str(info.get("sub"))
        email = (info.get("email") or "").lower()
        display_name = info.get("name") or email.split("@")[0]
    elif provider == "facebook":
        client = oauth.facebook
        client.authorize_access_token()
        info = client.get("me?fields=id,name,email").json()
        provider_user_id = str(info.get("id"))
        email = (info.get("email") or "").lower()
        display_name = info.get("name") or (email.split("@")[0] if email else "facebook-user")
    else:
        return redirect(url_for("auth.login"))

    if not provider_user_id or not email:
        flash("Dostawca logowania nie zwrócił adresu e-mail.", "error")
        return redirect(url_for("auth.login"))

    oauth_account = OAuthAccount.query.filter_by(
        provider=provider, provider_user_id=provider_user_id
    ).first()
    if oauth_account:
        user = oauth_account.user
    else:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email=email,
                username=_safe_username(email.split("@")[0]),
                display_name=display_name,
                preferred_language=g.lang,
            )
            db.session.add(user)
            db.session.flush()
        db.session.add(
            OAuthAccount(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
        )
        db.session.commit()

    _login_user(user)
    return redirect(url_for("shop.home"))
