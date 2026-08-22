from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from flask import Blueprint, current_app, g, jsonify, redirect, request, url_for
from sqlalchemy import or_

from .extensions import db
from .models import User, UserDialogueProfile, UserProfileObservation


shared_identity_bp = Blueprint("shared_identity", __name__)
PROFILE_KEYS = ("hylik", "psychik", "pneumatyk")
MAX_OBSERVATIONS_PER_USER = 120


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _profile_secret() -> str:
    return str(current_app.config.get("SOCRATIC_SHARED_AUTH_SECRET") or "")


def _require_shared_secret():
    secret = _profile_secret()
    provided = request.headers.get("X-Socratic-Shared-Secret", "")
    if len(secret) < 24 or not hmac.compare_digest(secret, provided):
        return jsonify({"error": "shared_identity_unauthorized"}), 401
    return None


def _user_payload(user: User) -> dict:
    return {
        "user_id": int(user.id),
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "preferred_language": user.preferred_language or "pl",
    }


def _get_or_create_profile(user: User) -> UserDialogueProfile:
    profile = user.dialogue_profile
    if profile is None:
        profile = UserDialogueProfile(user_id=user.id)
        db.session.add(profile)
        db.session.flush()
    return profile


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    clean = {key: max(0.0, _float(weights.get(key))) for key in PROFILE_KEYS}
    total = sum(clean.values())
    if total <= 0.0:
        return {"hylik": 1 / 3, "psychik": 1 / 3, "pneumatyk": 1 / 3}
    return {key: clean[key] / total for key in PROFILE_KEYS}


def _profile_payload(profile: UserDialogueProfile) -> dict:
    weights = _normalize(
        {
            "hylik": profile.hylik_weight,
            "psychik": profile.psychik_weight,
            "pneumatyk": profile.pneumatyk_weight,
        }
    )
    dominant = profile.dominant_profile
    if profile.sample_count <= 0 or dominant not in PROFILE_KEYS:
        dominant = "neutral"
    return {
        "user_id": int(profile.user_id),
        "hylik": round(weights["hylik"], 6),
        "psychik": round(weights["psychik"], 6),
        "pneumatyk": round(weights["pneumatyk"], 6),
        "percentages": {
            "hylik": round(weights["hylik"] * 100, 1),
            "psychik": round(weights["psychik"] * 100, 1),
            "pneumatyk": round(weights["pneumatyk"] * 100, 1),
        },
        "dominant_profile": dominant,
        "confidence": round(_float(profile.confidence), 6),
        "sample_count": int(profile.sample_count or 0),
        "profiling_enabled": bool(profile.profiling_enabled),
        "persisted": True,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "profile_kind": "dialogue_orientation",
        "non_diagnostic": True,
        "stores_raw_messages": False,
    }


def _signed_handoff(user: User, ttl_seconds: int = 120) -> str:
    secret = _profile_secret().encode("utf-8")
    if len(secret) < 24:
        raise RuntimeError("SOCRATIC_SHARED_AUTH_SECRET is not configured.")
    body = {
        "type": "ai_handoff",
        "user": _user_payload(user),
        "exp": int(time.time()) + max(60, int(ttl_seconds)),
    }
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = _b64encode(raw)
    signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}"


def _safe_language(value: str | None) -> str:
    return "en" if str(value or "").lower() == "en" else "pl"


def _shared_secret_configuration_error():
    if len(_profile_secret()) >= 24:
        return None
    return (
        jsonify(
            {
                "error": "shared_identity_not_configured",
                "detail": (
                    "Socratic shared identity is not configured. "
                    "Restart Socratic Store after configuring the shared secret."
                ),
            }
        ),
        503,
    )


def _ai_callback_url(token: str) -> str:
    base = str(current_app.config.get("SOCRATIC_AI_URL") or "http://localhost:8000").rstrip("/")
    return f"{base}/auth/callback?{urlencode({'token': token})}"


@shared_identity_bp.post("/api/shared/auth/login")
def shared_login():
    blocked = _require_shared_secret()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("identifier") or "").strip()
    password = str(data.get("password") or "")
    user = User.query.filter(
        or_(User.email == identifier.lower(), User.username == identifier)
    ).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify({"error": "Nieprawidłowy e-mail, nazwa użytkownika lub hasło."}), 401
    _get_or_create_profile(user)
    db.session.commit()
    return jsonify({"user": _user_payload(user)})


@shared_identity_bp.post("/api/shared/auth/register")
def shared_register():
    blocked = _require_shared_secret()
    if blocked:
        return blocked
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    language = _safe_language(data.get("preferred_language"))
    if not email or "@" not in email or len(username) < 3:
        return jsonify({"error": "Podaj poprawny e-mail i nazwę użytkownika."}), 400
    if len(password) < 8:
        return jsonify({"error": "Hasło musi mieć co najmniej 8 znaków."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Konto z tym adresem e-mail już istnieje."}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Ta nazwa użytkownika jest zajęta."}), 409
    user = User(
        email=email,
        username=username,
        display_name=username,
        preferred_language=language,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    _get_or_create_profile(user)
    db.session.commit()
    return jsonify({"user": _user_payload(user)}), 201


@shared_identity_bp.get("/api/shared/profile/<int:user_id>")
def shared_profile_get(user_id: int):
    blocked = _require_shared_secret()
    if blocked:
        return blocked
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Użytkownik nie istnieje."}), 404
    profile = _get_or_create_profile(user)
    db.session.commit()
    return jsonify({"profile": _profile_payload(profile)})


@shared_identity_bp.post("/api/shared/profile/<int:user_id>/observe")
def shared_profile_observe(user_id: int):
    blocked = _require_shared_secret()
    if blocked:
        return blocked
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Użytkownik nie istnieje."}), 404

    profile = _get_or_create_profile(user)
    if not profile.profiling_enabled:
        db.session.commit()
        return jsonify({"profile": _profile_payload(profile)})

    data = request.get_json(silent=True) or {}
    evidence_data = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    evidence = _normalize(evidence_data)
    strength = max(0.0, min(1.0, _float(evidence_data.get("strength"), 0.0)))
    if strength <= 0.05:
        db.session.commit()
        return jsonify({"profile": _profile_payload(profile)})

    previous = _normalize(
        {
            "hylik": profile.hylik_weight,
            "psychik": profile.psychik_weight,
            "pneumatyk": profile.pneumatyk_weight,
        }
    )
    alpha = 0.55 if int(profile.sample_count or 0) < 3 else 0.25
    alpha *= max(0.35, strength)
    mixed = {
        key: (1.0 - alpha) * previous[key] + alpha * evidence[key]
        for key in PROFILE_KEYS
    }
    updated = _normalize(mixed)
    ordered = sorted(updated.items(), key=lambda item: (-item[1], item[0]))
    sample_number = int(profile.sample_count or 0) + 1

    profile.hylik_weight = Decimal(f"{updated['hylik']:.6f}")
    profile.psychik_weight = Decimal(f"{updated['psychik']:.6f}")
    profile.pneumatyk_weight = Decimal(f"{updated['pneumatyk']:.6f}")
    profile.dominant_profile = ordered[0][0]
    profile.confidence = Decimal(f"{max(0.0, ordered[0][1] - ordered[1][1]):.6f}")
    profile.sample_count = sample_number
    conversation_id = str(data.get("conversation_id") or "").strip()[:128] or None
    profile.last_conversation_id = conversation_id
    profile.updated_at = datetime.utcnow()

    observation = UserProfileObservation(
        user_id=user.id,
        conversation_id=conversation_id,
        sample_number=sample_number,
        hylik_evidence=Decimal(f"{evidence['hylik']:.6f}"),
        psychik_evidence=Decimal(f"{evidence['psychik']:.6f}"),
        pneumatyk_evidence=Decimal(f"{evidence['pneumatyk']:.6f}"),
        evidence_strength=Decimal(f"{strength:.6f}"),
        resulting_dominant_profile=ordered[0][0],
    )
    db.session.add(observation)
    db.session.flush()

    # Retain only coarse recent observations. No raw prompt text is stored.
    count = UserProfileObservation.query.filter_by(user_id=user.id).count()
    if count > MAX_OBSERVATIONS_PER_USER:
        oldest = (
            UserProfileObservation.query
            .filter_by(user_id=user.id)
            .order_by(UserProfileObservation.id.asc())
            .limit(count - MAX_OBSERVATIONS_PER_USER)
            .all()
        )
        for item in oldest:
            db.session.delete(item)

    db.session.commit()
    return jsonify({"profile": _profile_payload(profile)})


@shared_identity_bp.post("/api/shared/profile/<int:user_id>/settings")
def shared_profile_settings(user_id: int):
    blocked = _require_shared_secret()
    if blocked:
        return blocked
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Użytkownik nie istnieje."}), 404
    profile = _get_or_create_profile(user)
    data = request.get_json(silent=True) or {}
    if "profiling_enabled" in data:
        profile.profiling_enabled = bool(data.get("profiling_enabled"))
        profile.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"profile": _profile_payload(profile)})


@shared_identity_bp.post("/api/shared/profile/<int:user_id>/reset")
def shared_profile_reset(user_id: int):
    blocked = _require_shared_secret()
    if blocked:
        return blocked
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Użytkownik nie istnieje."}), 404
    profile = _get_or_create_profile(user)
    profile.hylik_weight = Decimal("0.333333")
    profile.psychik_weight = Decimal("0.333333")
    profile.pneumatyk_weight = Decimal("0.333334")
    profile.dominant_profile = "neutral"
    profile.confidence = Decimal("0.000000")
    profile.sample_count = 0
    profile.last_conversation_id = None
    profile.updated_at = datetime.utcnow()
    UserProfileObservation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"profile": _profile_payload(profile)})


@shared_identity_bp.get("/auth/bridge/ai")
def ai_bridge():
    language = _safe_language(request.args.get("lang") or g.get("lang"))
    if not g.get("user"):
        next_path = url_for("shared_identity.ai_bridge", lang=language)
        return redirect(url_for("auth.login", next=next_path))

    configuration_error = _shared_secret_configuration_error()
    if configuration_error:
        return configuration_error

    token = _signed_handoff(g.user)
    return redirect(_ai_callback_url(token))


@shared_identity_bp.get("/auth/bridge/ai/oauth/<provider>")
def ai_oauth_bridge(provider: str):
    if provider not in {"google", "facebook"}:
        return redirect(url_for("auth.login"))

    configuration_error = _shared_secret_configuration_error()
    if configuration_error:
        return configuration_error

    language = _safe_language(request.args.get("lang") or g.get("lang"))
    return redirect(
        url_for(
            "auth.oauth_login",
            provider=provider,
            return_to="ai",
            lang=language,
        )
    )
