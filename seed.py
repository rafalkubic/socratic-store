from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Category, Product


CATEGORIES = [
    {"slug": "books", "name_pl": "Książki", "name_en": "Books", "sort_order": 1},
    {"slug": "merch", "name_pl": "Merch", "name_en": "Merch", "sort_order": 2},
    {"slug": "art", "name_pl": "Sztuka", "name_en": "Art", "sort_order": 3},
    {"slug": "other", "name_pl": "Inne", "name_en": "Other", "sort_order": 4},
]

PRODUCTS = [
    {
        "category": "books",
        "sku": "BOOK-DANTE-001",
        "slug": "dante-boska-komedia",
        "name_pl": "Dante — Boska Komedia",
        "name_en": "Dante — Divine Comedy",
        "description_pl": "Klasyczna podróż przez Piekło, Czyściec i Raj — wydanie dla czytelników zainteresowanych symboliką, metafizyką i historią idei.",
        "description_en": "A classic journey through Inferno, Purgatorio and Paradiso for readers drawn to symbolism, metaphysics and the history of ideas.",
        "price_pln": Decimal("79.00"),
        "stock_qty": 24,
        "image_path": "images/products/dante.jpg",
    },
    {
        "category": "books",
        "sku": "BOOK-JUNG-001",
        "slug": "jung-archetypy-nieswiadomosc",
        "name_pl": "C.G. Jung — Archetypy i nieświadomość zbiorowa",
        "name_en": "C.G. Jung — Archetypes and the Collective Unconscious",
        "description_pl": "Wprowadzenie do jungowskiej teorii archetypów, symboli i nieświadomości zbiorowej — fundament dla pracy z mitami i wyobraźnią.",
        "description_en": "An introduction to Jung's theory of archetypes, symbols and the collective unconscious — a foundation for exploring myth and imagination.",
        "price_pln": Decimal("89.00"),
        "stock_qty": 18,
        "image_path": "images/products/jung.jpg",
    },
    {
        "category": "merch",
        "sku": "MERCH-TOOL-001",
        "slug": "tool-lateralus-shirt",
        "name_pl": "Tool — Lateralus T-shirt",
        "name_en": "Tool — Lateralus T-shirt",
        "description_pl": "Czarny T-shirt inspirowany estetyką albumu Lateralus, z kontrastowym motywem oka i płomienia.",
        "description_en": "Black T-shirt inspired by the Lateralus visual language, featuring a high-contrast eye-and-flame motif.",
        "price_pln": Decimal("99.00"),
        "stock_qty": 30,
        "image_path": "images/products/tool.jpg",
    },
    {
        "category": "merch",
        "sku": "MERCH-TOOL-002",
        "slug": "tool-anatomy-shirt",
        "name_pl": "Tool — Anatomy T-shirt",
        "name_en": "Tool — Anatomy T-shirt",
        "description_pl": "Czarny T-shirt z anatomiczną grafiką w psychodelicznej stylistyce, nawiązującą do warstw ciała i świadomości.",
        "description_en": "Black T-shirt with a psychedelic anatomical illustration evoking the layered relationship between body and consciousness.",
        "price_pln": Decimal("109.00"),
        "stock_qty": 26,
        "image_path": "images/products/tool-2.jpg",
    },
    {
        "category": "art",
        "sku": "ART-MANDALA-001",
        "slug": "mandala-pink-blue",
        "name_pl": "Mandala I — Geometria różowo-granatowa",
        "name_en": "Mandala I — Pink & Navy Geometry",
        "description_pl": "Dekoracyjna praca oparta na warstwowych wielokątach, symetrii radialnej i motywach świętej geometrii.",
        "description_en": "A decorative work built from layered polygons, radial symmetry and motifs drawn from sacred geometry.",
        "price_pln": Decimal("1800.00"),
        "stock_qty": 1,
        "image_path": "images/products/mandala.jpg",
    },
    {
        "category": "art",
        "sku": "ART-MANDALA-002",
        "slug": "mandala-monochrome",
        "name_pl": "Mandala II — Monochromatyczna geometria",
        "name_en": "Mandala II — Monochrome Geometry",
        "description_pl": "Monochromatyczna kompozycja o gęstej strukturze, łącząca mandalę, ornament i matematyczny rytm.",
        "description_en": "A dense monochrome composition combining mandala structure, ornament and mathematical rhythm.",
        "price_pln": Decimal("2200.00"),
        "stock_qty": 1,
        "image_path": "images/products/mandala2.jpg",
    },
    {
        "category": "other",
        "sku": "OTHER-FRANKIN-001",
        "slug": "frankin-incense-burner",
        "name_pl": "Frankin — ceramiczna kadzielnica",
        "name_en": "Frankin — Ceramic Incense Burner",
        "description_pl": "Niewielka ceramiczna kadzielnica do żywic i mieszanek zapachowych, przeznaczona do stworzenia spokojnej, rytualnej atmosfery.",
        "description_en": "A compact ceramic incense burner for resins and aromatic blends, designed to create a calm, ritual-like atmosphere.",
        "price_pln": Decimal("149.00"),
        "stock_qty": 12,
        "image_path": "images/products/frankin.jpg",
    },
]


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        category_map = {}
        for item in CATEGORIES:
            category = Category.query.filter_by(slug=item["slug"]).first()
            if not category:
                category = Category(**item)
                db.session.add(category)
                db.session.flush()
            else:
                category.name_pl = item["name_pl"]
                category.name_en = item["name_en"]
                category.sort_order = item["sort_order"]
            category_map[item["slug"]] = category

        for item in PRODUCTS:
            payload = dict(item)
            category_slug = payload.pop("category")
            product = Product.query.filter_by(sku=payload["sku"]).first()
            if not product:
                product = Product(category_id=category_map[category_slug].id, **payload)
                db.session.add(product)
            else:
                product.category_id = category_map[category_slug].id
                for key, value in payload.items():
                    setattr(product, key, value)
        db.session.commit()
        print(f"Seed complete: {Category.query.count()} categories, {Product.query.count()} products.")


if __name__ == "__main__":
    seed()
