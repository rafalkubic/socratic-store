from __future__ import annotations

import re

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from .extensions import db, oauth
from .models import OAuthAccount, User, UserDialogueProfile
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


def _safe_next_path(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return None


def _login_user(user: User) -> None:
    cart = session.get("cart", {})
    lang = session.get("lang") or user.preferred_language or "pl"
    session.clear()
    session["user_id"] = user.id
    session["lang"] = lang
    session["cart"] = cart


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    next_path = _safe_next_path(request.values.get("next"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_repeat = request.form.get("password_repeat", "")

        def render_again():
            return render_template("register.html", next_path=next_path)

        if not email or "@" not in email or not username:
            flash("Uzupełnij poprawnie e-mail i nazwę użytkownika.", "error")
            return render_again()
        if password != password_repeat:
            flash(_t("password_mismatch"), "error")
            return render_again()
        if len(password) < 8:
            flash(_t("password_short"), "error")
            return render_again()
        if User.query.filter_by(email=email).first():
            flash(_t("email_exists"), "error")
            return render_again()
        if User.query.filter_by(username=username).first():
            flash(_t("username_exists"), "error")
            return render_again()

        user = User(email=email, username=username, display_name=username, preferred_language=g.lang)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(UserDialogueProfile(user_id=user.id))
        db.session.commit()
        _login_user(user)
        flash(_t("account_created"), "success")
        return redirect(next_path or url_for("shop.home"))

    return render_template("register.html", next_path=next_path)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_path = _safe_next_path(request.values.get("next"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(or_(User.email == identifier.lower(), User.username == identifier)).first()
        if not user or not user.is_active or not user.check_password(password):
            flash(_t("invalid_credentials"), "error")
            return render_template("login.html", next_path=next_path)
        _login_user(user)
        return redirect(next_path or url_for("shop.home"))
    return render_template("login.html", next_path=next_path)


@auth_bp.post("/logout")
def logout():
    lang = session.get("lang", "pl")
    session.clear()
    session["lang"] = lang
    return redirect(url_for("shop.home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = g.get("user")
    if user is None:
        return redirect(url_for("auth.login", next=url_for("auth.profile")))
    profile = user.dialogue_profile
    if profile is None:
        profile = UserDialogueProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        action = request.form.get("action", "settings")
        if action == "reset":
            from .models import UserProfileObservation
            from decimal import Decimal
            profile.hylik_weight = Decimal("0.333333")
            profile.psychik_weight = Decimal("0.333333")
            profile.pneumatyk_weight = Decimal("0.333334")
            profile.dominant_profile = "neutral"
            profile.confidence = Decimal("0.000000")
            profile.sample_count = 0
            profile.last_conversation_id = None
            UserProfileObservation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            db.session.commit()
            flash(_t("profile_reset_done"), "success")
        else:
            profile.profiling_enabled = request.form.get("profiling_enabled") == "on"
            db.session.commit()
            flash(_t("profile_saved"), "success")
        return redirect(url_for("auth.profile"))

    weights = {
        "hylik": float(profile.hylik_weight or 0),
        "psychik": float(profile.psychik_weight or 0),
        "pneumatyk": float(profile.pneumatyk_weight or 0),
    }
    total = sum(weights.values()) or 1.0
    percentages = {key: round(value / total * 100, 1) for key, value in weights.items()}
    dominant = profile.dominant_profile if profile.sample_count else "neutral"
    return render_template(
        "profile.html",
        dialogue_profile=profile,
        profile_percentages=percentages,
        profile_dominant=dominant,
    )


@auth_bp.get("/oauth/<provider>")
def oauth_login(provider: str):
    return_to = request.args.get("return_to")
    if return_to == "ai":
        session["oauth_return_to"] = "ai"
    requested_lang = request.args.get("lang")
    if requested_lang in {"pl", "en"}:
        session["lang"] = requested_lang
        g.lang = requested_lang
    if provider not in {"google", "facebook"}:
        return redirect(url_for("auth.login"))

    if provider == "google":
        if not current_app.config.get("GOOGLE_CLIENT_ID") or not current_app.config.get("GOOGLE_CLIENT_SECRET"):
            flash(_t("oauth_not_configured"), "error")
            next_path = url_for("shared_identity.ai_bridge", lang=g.lang) if return_to == "ai" else None
            return redirect(url_for("auth.login", next=next_path) if next_path else url_for("auth.login"))
        client = oauth.google
    else:
        if not current_app.config.get("FACEBOOK_CLIENT_ID") or not current_app.config.get("FACEBOOK_CLIENT_SECRET"):
            flash(_t("oauth_not_configured"), "error")
            next_path = url_for("shared_identity.ai_bridge", lang=g.lang) if return_to == "ai" else None
            return redirect(url_for("auth.login", next=next_path) if next_path else url_for("auth.login"))
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

    return_to = session.get("oauth_return_to")
    if user.dialogue_profile is None:
        db.session.add(UserDialogueProfile(user_id=user.id))
        db.session.commit()
    _login_user(user)
    if return_to == "ai":
        return redirect(url_for("shared_identity.ai_bridge", lang=g.lang))
    return redirect(url_for("shop.home"))
