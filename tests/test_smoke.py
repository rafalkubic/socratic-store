import os

os.environ.setdefault("SECRET_KEY", "test-secret")

from app import create_app
from app.extensions import db
from app.models import Category, Product, User, UserDialogueProfile, UserProfileObservation


def make_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SOCRATIC_SHARED_AUTH_SECRET": "test-shared-secret-that-is-long-enough",
            "SOCRATIC_AI_URL": "http://localhost:8000",
        }
    )
    with app.app_context():
        db.create_all()
        cat = Category(slug="books", name_pl="Książki", name_en="Books", sort_order=1)
        db.session.add(cat)
        db.session.flush()
        db.session.add(
            Product(
                category_id=cat.id,
                sku="TEST-1",
                slug="test-product",
                name_pl="Test",
                name_en="Test",
                description_pl="Opis",
                description_en="Description",
                price_pln=10,
                stock_qty=1,
                image_path="images/products/dante.jpg",
            )
        )
        db.session.commit()
    return app


def test_homepage_and_product():
    app = make_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Socratic Store" in response.data
    response = client.get("/product/test-product")
    assert response.status_code == 200


def test_language_switch():
    app = make_app()
    client = app.test_client()
    response = client.get("/lang/en", follow_redirects=True)
    assert response.status_code == 200
    assert b"Browse collection" in response.data


SHARED_HEADERS = {"X-Socratic-Shared-Secret": "test-shared-secret-that-is-long-enough"}


def create_user(app, email="profile@example.com", username="profile-user", password="password123"):
    with app.app_context():
        user = User(
            email=email,
            username=username,
            display_name="Profile User",
            preferred_language="pl",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def test_shared_local_registration_is_visible_to_store_login():
    app = make_app()
    client = app.test_client()
    response = client.post(
        "/api/shared/auth/register",
        json={
            "email": "new@example.com",
            "username": "new-user",
            "password": "password123",
            "preferred_language": "pl",
        },
        headers=SHARED_HEADERS,
    )
    assert response.status_code == 201
    user_id = response.get_json()["user"]["user_id"]
    with app.app_context():
        assert db.session.get(User, user_id) is not None
        assert db.session.get(UserDialogueProfile, user_id) is not None

    response = client.post(
        "/auth/login",
        data={"identifier": "new@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] == user_id


def test_store_created_account_can_use_shared_ai_login():
    app = make_app()
    user_id = create_user(app)
    client = app.test_client()
    response = client.post(
        "/api/shared/auth/login",
        json={"identifier": "profile@example.com", "password": "password123"},
        headers=SHARED_HEADERS,
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["user_id"] == user_id


def test_profile_observations_are_numeric_only_and_adaptive():
    app = make_app()
    user_id = create_user(app)
    client = app.test_client()

    for sample in range(3):
        response = client.post(
            f"/api/shared/profile/{user_id}/observe",
            json={
                "conversation_id": "conv-profile",
                "evidence": {
                    "hylik": 0.9,
                    "psychik": 0.08,
                    "pneumatyk": 0.02,
                    "strength": 1.0,
                },
            },
            headers=SHARED_HEADERS,
        )
        assert response.status_code == 200

    profile = response.get_json()["profile"]
    assert profile["sample_count"] == 3
    assert profile["dominant_profile"] == "hylik"
    assert profile["hylik"] > 0.75
    assert profile["stores_raw_messages"] is False

    # A sustained new direction can move the profile.
    for sample in range(8):
        response = client.post(
            f"/api/shared/profile/{user_id}/observe",
            json={
                "conversation_id": "conv-profile",
                "evidence": {
                    "hylik": 0.02,
                    "psychik": 0.96,
                    "pneumatyk": 0.02,
                    "strength": 1.0,
                },
            },
            headers=SHARED_HEADERS,
        )
    profile = response.get_json()["profile"]
    assert profile["dominant_profile"] == "psychik"
    with app.app_context():
        observation = UserProfileObservation.query.first()
        assert observation is not None
        assert not hasattr(observation, "message")
        assert not hasattr(observation, "prompt")


def test_profile_can_be_disabled_and_reset():
    app = make_app()
    user_id = create_user(app)
    client = app.test_client()
    response = client.post(
        f"/api/shared/profile/{user_id}/settings",
        json={"profiling_enabled": False},
        headers=SHARED_HEADERS,
    )
    assert response.status_code == 200
    assert response.get_json()["profile"]["profiling_enabled"] is False

    response = client.post(
        f"/api/shared/profile/{user_id}/reset",
        json={},
        headers=SHARED_HEADERS,
    )
    profile = response.get_json()["profile"]
    assert profile["sample_count"] == 0
    assert profile["dominant_profile"] == "neutral"
    assert profile["profiling_enabled"] is False


def test_shared_api_rejects_missing_secret():
    app = make_app()
    client = app.test_client()
    response = client.post(
        "/api/shared/auth/login",
        json={"identifier": "x", "password": "y"},
    )
    assert response.status_code == 401


def test_active_store_session_returns_controlled_503_when_shared_secret_missing():
    app = make_app()
    app.config["SOCRATIC_SHARED_AUTH_SECRET"] = ""
    user_id = create_user(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["lang"] = "pl"

    response = client.get("/auth/bridge/ai", follow_redirects=False)

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["error"] == "shared_identity_not_configured"


def test_active_store_session_can_handoff_to_ai():
    app = make_app()
    user_id = create_user(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["lang"] = "pl"
    response = client.get("/auth/bridge/ai", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("http://localhost:8000/auth/callback?token=")


def test_store_profile_page_exposes_three_orientations():
    app = make_app()
    user_id = create_user(app)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["lang"] = "pl"
    response = client.get("/auth/profile")
    assert response.status_code == 200
    assert "Hylik" in response.get_data(as_text=True)
    assert "Psychik" in response.get_data(as_text=True)
    assert "Pneumatyk" in response.get_data(as_text=True)
