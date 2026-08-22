from __future__ import annotations

from decimal import Decimal

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
        # Cena demonstracyjna – można później zmienić w MySQL lub skrypcie.
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
        # Cena demonstracyjna – można później zmienić w MySQL lub skrypcie.
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

        changed = []

        for payload in BOOKS:
            product = Product.query.filter_by(sku=payload["sku"]).first()

            if product is None:
                product = Product(
                    category_id=books_category.id,
                    **payload,
                )
                db.session.add(product)
                action = "ADDED"
            else:
                product.category_id = books_category.id
                for key, value in payload.items():
                    # Do not unexpectedly replenish stock on reinstall if the item
                    # already exists. Preserve the real current stock quantity.
                    if key == "stock_qty":
                        continue
                    setattr(product, key, value)
                action = "UPDATED"

            changed.append((action, payload["sku"], payload["name_pl"]))

        db.session.commit()

        print("")
        print("Socratic Store - Rijckenborgh books update")
        print("-----------------------------------------")
        for action, sku, name in changed:
            product = Product.query.filter_by(sku=sku).first()
            print(
                f"{action}: id={product.id}, sku={sku}, "
                f"title={name}, price={product.price_pln} PLN, stock={product.stock_qty}"
            )
        print("")
        print(f"Total active products: {Product.query.filter_by(is_active=True).count()}")


if __name__ == "__main__":
    upsert_books()
