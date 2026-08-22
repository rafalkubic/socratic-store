from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

# When a script is launched as:
#   python C:\...\socratic_store\scripts\add_rijckenborgh_books.py
# Python puts only the "scripts" directory on sys.path. Add the project root
# explicitly so imports such as "from app import create_app" work on Windows.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models import Category, Product


BOOKS = [
    {
        "sku": "BOOK-RIJCKENBORGH-ALCHEMICAL-001",
        "slug": "jan-van-rijckenborgh-alchemiczne-gody",
        "name_pl": "Alchemiczne gody Chrystiana Różokrzyża",
        "name_en": "The Alchemical Wedding of Christian Rosycross",
        "description_pl": (
            "Ezoteryczna interpretacja symbolicznej opowieści o godach Chrystiana "
            "Różokrzyża. Jan van Rijckenborgh prowadzi czytelnika przez obrazy przemiany, "
            "inicjacji i duchowego odrodzenia, odczytując tekst w tradycji różokrzyżowej."
        ),
        "description_en": (
            "An esoteric reading of the symbolic story of the wedding of Christian "
            "Rosycross. Jan van Rijckenborgh explores themes of transformation, initiation "
            "and spiritual renewal through a Rosicrucian lens."
        ),
        "price_pln": Decimal("59.00"),
        "stock_qty": 10,
        "image_path": "images/products/rijckenborgh-alchemiczne-gody.jpg",
        "is_active": True,
    },
    {
        "sku": "BOOK-RIJCKENBORGH-NEWMAN-001",
        "slug": "jan-van-rijckenborgh-nadchodzacy-nowy-czlowiek",
        "name_pl": "Nadchodzący nowy człowiek",
        "name_en": "The Coming New Man",
        "description_pl": (
            "Książka poświęcona idei wewnętrznej przemiany człowieka i przekroczenia "
            "utrwalonych wzorców świadomości. Autor przedstawia duchową drogę prowadzącą "
            "ku nowemu sposobowi rozumienia siebie, świata i odpowiedzialności."
        ),
        "description_en": (
            "A work devoted to inner human transformation and the transcendence of fixed "
            "patterns of consciousness. The author presents a spiritual path toward a new "
            "understanding of the self, the world and personal responsibility."
        ),
        "price_pln": Decimal("69.00"),
        "stock_qty": 10,
        "image_path": "images/products/rijckenborgh-nadchodzacy-nowy-czlowiek.jpg",
        "is_active": True,
    },
]


def upsert_books() -> None:
    app = create_app()

    with app.app_context():
        books_category = Category.query.filter_by(slug="books").first()

        if books_category is None:
            books_category = Category(
                slug="books",
                name_pl="Książki",
                name_en="Books",
                sort_order=1,
            )
            db.session.add(books_category)
            db.session.flush()

        results = []

        for payload in BOOKS:
            product = Product.query.filter_by(sku=payload["sku"]).first()

            if product is None:
                product = Product(category_id=books_category.id, **payload)
                db.session.add(product)
                action = "ADDED"
            else:
                product.category_id = books_category.id

                # Preserve live stock on repeated installations.
                for key, value in payload.items():
                    if key == "stock_qty":
                        continue
                    setattr(product, key, value)

                action = "UPDATED"

            db.session.flush()
            results.append((action, product.id, product.sku, product.name_pl))

        db.session.commit()

        print("")
        print("Socratic Store - Rijckenborgh books update V10.1")
        print("------------------------------------------------")
        for action, product_id, sku, name in results:
            product = db.session.get(Product, product_id)
            print(
                f"{action}: id={product.id}, sku={sku}, title={name}, "
                f"price={product.price_pln} PLN, stock={product.stock_qty}"
            )

        print("")
        print(f"Total active products: {Product.query.filter_by(is_active=True).count()}")


if __name__ == "__main__":
    upsert_books()
