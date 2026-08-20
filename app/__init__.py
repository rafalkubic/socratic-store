from __future__ import annotations

from flask import Flask, g, session
from dotenv import load_dotenv

from .config import Config
from .extensions import csrf, db, oauth
from .models import Category, User
from .translations import translate


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    fb_version = app.config.get("FACEBOOK_GRAPH_VERSION", "v26.0")
    oauth.register(
        name="facebook",
        client_id=app.config.get("FACEBOOK_CLIENT_ID"),
        client_secret=app.config.get("FACEBOOK_CLIENT_SECRET"),
        access_token_url=f"https://graph.facebook.com/{fb_version}/oauth/access_token",
        authorize_url=f"https://www.facebook.com/{fb_version}/dialog/oauth",
        api_base_url=f"https://graph.facebook.com/{fb_version}/",
        client_kwargs={"scope": "email,public_profile"},
    )

    from .auth import auth_bp
    from .payments import payments_bp
    from .shop import shop_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(payments_bp)

    @app.before_request
    def load_user_and_language():
        lang = session.get("lang", "pl")
        if lang not in {"pl", "en"}:
            lang = "pl"
        g.lang = lang
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = db.session.get(User, user_id)

    @app.context_processor
    def inject_globals():
        categories = Category.query.order_by(Category.sort_order, Category.id).all()
        return {
            "current_user": g.get("user"),
            "lang": g.get("lang", "pl"),
            "t": lambda key: translate(g.get("lang", "pl"), key),
            "nav_categories": categories,
            "shop_name": app.config["SHOP_NAME"],
            "socratic_ai_url": app.config["SOCRATIC_AI_URL"],
            "demo_payment_mode": app.config["DEMO_PAYMENT_MODE"],
            "p24_enabled": app.config["P24_ENABLED"],
        }

    @app.template_filter("money")
    def money(value):
        return f"{value:.2f} zł".replace(".", ",") if g.get("lang") == "pl" else f"PLN {value:.2f}"

    return app
