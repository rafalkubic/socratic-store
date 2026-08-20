import os

os.environ.setdefault("SECRET_KEY", "test-secret")

from app import create_app
from app.extensions import db
from app.models import Category, Product


def make_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
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
