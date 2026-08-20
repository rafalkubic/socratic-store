-- Optional SQL-only seed. The recommended seed path is `python seed.py`.
INSERT INTO categories (slug, name_pl, name_en, sort_order) VALUES
('books','Książki','Books',1),
('merch','Merch','Merch',2),
('art','Sztuka','Art',3),
('other','Inne','Other',4)
ON DUPLICATE KEY UPDATE name_pl=VALUES(name_pl), name_en=VALUES(name_en), sort_order=VALUES(sort_order);

INSERT INTO products
(category_id, sku, slug, name_pl, name_en, description_pl, description_en, price_pln, stock_qty, image_path, is_active)
VALUES
((SELECT id FROM categories WHERE slug='books'),'BOOK-DANTE-001','dante-boska-komedia','Dante — Boska Komedia','Dante — Divine Comedy','Klasyczna podróż przez Piekło, Czyściec i Raj — wydanie dla czytelników zainteresowanych symboliką, metafizyką i historią idei.','A classic journey through Inferno, Purgatorio and Paradiso for readers drawn to symbolism, metaphysics and the history of ideas.',79.00,24,'images/products/dante.jpg',1),
((SELECT id FROM categories WHERE slug='books'),'BOOK-JUNG-001','jung-archetypy-nieswiadomosc','C.G. Jung — Archetypy i nieświadomość zbiorowa','C.G. Jung — Archetypes and the Collective Unconscious','Wprowadzenie do jungowskiej teorii archetypów, symboli i nieświadomości zbiorowej — fundament dla pracy z mitami i wyobraźnią.','An introduction to Jung''s theory of archetypes, symbols and the collective unconscious — a foundation for exploring myth and imagination.',89.00,18,'images/products/jung.jpg',1),
((SELECT id FROM categories WHERE slug='merch'),'MERCH-TOOL-001','tool-lateralus-shirt','Tool — Lateralus T-shirt','Tool — Lateralus T-shirt','Czarny T-shirt inspirowany estetyką albumu Lateralus, z kontrastowym motywem oka i płomienia.','Black T-shirt inspired by the Lateralus visual language, featuring a high-contrast eye-and-flame motif.',99.00,30,'images/products/tool.jpg',1),
((SELECT id FROM categories WHERE slug='merch'),'MERCH-TOOL-002','tool-anatomy-shirt','Tool — Anatomy T-shirt','Tool — Anatomy T-shirt','Czarny T-shirt z anatomiczną grafiką w psychodelicznej stylistyce, nawiązującą do warstw ciała i świadomości.','Black T-shirt with a psychedelic anatomical illustration evoking the layered relationship between body and consciousness.',109.00,26,'images/products/tool-2.jpg',1),
((SELECT id FROM categories WHERE slug='art'),'ART-MANDALA-001','mandala-pink-blue','Mandala I — Geometria różowo-granatowa','Mandala I — Pink & Navy Geometry','Dekoracyjna praca oparta na warstwowych wielokątach, symetrii radialnej i motywach świętej geometrii.','A decorative work built from layered polygons, radial symmetry and motifs drawn from sacred geometry.',1800.00,1,'images/products/mandala.jpg',1),
((SELECT id FROM categories WHERE slug='art'),'ART-MANDALA-002','mandala-monochrome','Mandala II — Monochromatyczna geometria','Mandala II — Monochrome Geometry','Monochromatyczna kompozycja o gęstej strukturze, łącząca mandalę, ornament i matematyczny rytm.','A dense monochrome composition combining mandala structure, ornament and mathematical rhythm.',2200.00,1,'images/products/mandala2.jpg',1),
((SELECT id FROM categories WHERE slug='other'),'OTHER-FRANKIN-001','frankin-incense-burner','Frankin — ceramiczna kadzielnica','Frankin — Ceramic Incense Burner','Niewielka ceramiczna kadzielnica do żywic i mieszanek zapachowych, przeznaczona do stworzenia spokojnej, rytualnej atmosfery.','A compact ceramic incense burner for resins and aromatic blends, designed to create a calm, ritual-like atmosphere.',149.00,12,'images/products/frankin.jpg',1)
ON DUPLICATE KEY UPDATE
category_id=VALUES(category_id), slug=VALUES(slug), name_pl=VALUES(name_pl), name_en=VALUES(name_en),
description_pl=VALUES(description_pl), description_en=VALUES(description_en), price_pln=VALUES(price_pln),
stock_qty=VALUES(stock_qty), image_path=VALUES(image_path), is_active=VALUES(is_active);
