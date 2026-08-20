# Socratic Store — Flask + MySQL

Prosty, dwujęzyczny sklep internetowy w stylistyce czerni, złota i świętej geometrii, przygotowany na podstawie dostarczonych obrazów. Backend jest napisany w Pythonie/Flask, dane są relacyjne i przechowywane w MySQL, a frontend używa zwykłych szablonów Jinja + CSS.

## Co jest w projekcie

- kategorie: **Książki / Books**, **Merch**, **Sztuka / Art**, **Inne / Other**,
- produkty z dostarczonych obrazów: Dante, Jung, Tool, Tool 2, Mandala I, Mandala II, Frankin,
- polska i angielska wersja językowa przełączana w nagłówku,
- konto lokalne: rejestracja, logowanie, bezpieczne hashowanie hasła,
- logowanie Google OAuth/OIDC,
- logowanie Facebook/Meta OAuth,
- koszyk i zamówienia,
- płatności przez **Przelewy24** — docelowo BLIK i przelewy bankowe dostępne w konfiguracji operatora,
- tryb płatności DEMO do lokalnego testowania bez pobierania pieniędzy,
- link powrotny do istniejącego systemu Socratic AI przez `SOCRATIC_AI_URL`,
- MySQL przez instalację lokalną lub Docker Compose,
- SQL schema + idempotentny seed w Pythonie.

> Ceny w danych startowych są przykładowe. Przed publikacją zmień je na właściwe ceny i upewnij się, że masz prawa do sprzedaży produktów oraz używania grafik.

## Dlaczego obrazy nie są Base64 w MySQL

Wybrałem **ścieżki do plików** zamiast Base64. Rekord `products.image_path` wskazuje na plik w `app/static/images/products/`. To rozwiązanie jest lżejsze dla bazy, szybsze w serwowaniu, łatwiejsze do cache'owania i późniejszego przeniesienia na CDN/object storage. Baza przechowuje metadane, nie duże binaria.

## Struktura

```text
socratic_store/
├── app/
│   ├── __init__.py
│   ├── auth.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── payments.py
│   ├── shop.py
│   ├── translations.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── images/
│   │       ├── products/
│   │       └── decor/
│   └── templates/
├── scripts/
│   ├── install_mysql_ubuntu.sh
│   └── init_db.sql
├── tests/test_smoke.py
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── run.py
├── schema.sql
└── seed.py
```

# 1. Najszybsze uruchomienie — MySQL w Dockerze

Wymagania: Python 3.10+ i Docker z `docker compose`.

```bash
cd socratic_store
cp .env.example .env

docker compose up -d mysql

python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python seed.py
python run.py
```

Otwórz:

```text
http://localhost:5000
```

Domyślne lokalne dane MySQL z `docker-compose.yml` i `.env.example`:

```text
DB:       socratic_store
User:     socratic_store
Password: change-me
Host:     127.0.0.1:3306
```

To są wyłącznie dane developerskie — zmień hasła przed jakimkolwiek wdrożeniem poza lokalnym komputerem.

# 2. Lokalna instalacja MySQL na Ubuntu/Debian

Skrypt instaluje `mysql-server`, uruchamia usługę i tworzy bazę oraz użytkownika aplikacji.

```bash
cd socratic_store
MYSQL_APP_PASSWORD='tu-mocne-lokalne-haslo' ./scripts/install_mysql_ubuntu.sh
```

Następnie ustaw `DATABASE_URL` w `.env`, np.:

```env
DATABASE_URL=mysql+pymysql://socratic_store:tu-mocne-lokalne-haslo@127.0.0.1:3306/socratic_store?charset=utf8mb4
```

I uruchom aplikację:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python run.py
```

`seed.py` tworzy tabele przez SQLAlchemy (`db.create_all()`) i dodaje/aktualizuje kategorie oraz 7 produktów. `schema.sql` zawiera równoważny, jawny schemat relacyjny MySQL do wglądu lub ręcznego wdrożenia.

# 3. Model relacyjny

Najważniejsze relacje:

```text
users 1 ─── n oauth_accounts
users 1 ─── n orders
categories 1 ─── n products
orders 1 ─── n order_items
products 1 ─── n order_items
orders 1 ─── n payment_transactions
```

`order_items` przechowują snapshot nazwy i ceny z momentu zakupu, więc późniejsza zmiana produktu nie zmieni historycznego zamówienia.

# 4. Logowanie Google

W Google Cloud utwórz OAuth Client typu **Web application**. Dla pracy lokalnej ustaw redirect URI:

```text
http://localhost:5000/auth/oauth/google/callback
```

Potem wpisz do `.env`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Aplikacja używa OIDC/OAuth przez bibliotekę Authlib i prosi wyłącznie o `openid email profile`.

Oficjalna dokumentacja:

```text
https://developers.google.com/identity/openid-connect/openid-connect
https://developers.google.com/identity/protocols/oauth2/web-server
```

# 5. Logowanie Facebook / Meta

Utwórz aplikację w Meta for Developers i skonfiguruj Facebook Login. Redirect URI aplikacji:

```text
http://localhost:5000/auth/oauth/facebook/callback
```

W `.env`:

```env
FACEBOOK_CLIENT_ID=...
FACEBOOK_CLIENT_SECRET=...
FACEBOOK_GRAPH_VERSION=v26.0
```

Wersja Graph API jest konfigurowalna przez `.env`, żeby można ją było łatwo zaktualizować bez przebudowy aplikacji.

Oficjalna dokumentacja:

```text
https://developers.facebook.com/documentation/facebook-login
https://developers.facebook.com/docs/graph-api/changelog/versions/
```

# 6. Przelewy24 — BLIK / bank transfer

Kod zawiera integrację REST P24:

1. aplikacja zapisuje zamówienie i `payment_transactions`,
2. serwer rejestruje transakcję w P24,
3. klient jest przekierowany do bramki Przelewy24,
4. P24 wywołuje `urlStatus`,
5. sklep sprawdza podpis i wykonuje `transaction/verify`,
6. dopiero po poprawnej weryfikacji zamówienie dostaje status `paid` i magazyn jest pomniejszany.

Konfiguracja `.env`:

```env
P24_ENABLED=true
P24_SANDBOX=true
P24_MERCHANT_ID=...
P24_POS_ID=...
P24_API_KEY=...
P24_CRC=...
```

Oficjalna dokumentacja P24:

```text
https://developers.przelewy24.pl/
```

## Ważne przy pracy lokalnej

Przekierowanie przeglądarki do P24 może działać z lokalnej aplikacji, ale **serwer P24 nie wywoła webhooka pod `localhost`**. Do pełnego testu sandbox potrzebujesz publicznego adresu HTTPS kierującego do lokalnego portu, np. tunelu developerskiego. Wtedy ustaw:

```env
APP_BASE_URL=https://twoj-publiczny-adres-testowy.example
```

Endpoint statusu to:

```text
POST /payments/p24/status
```

Dostępność konkretnych banków i BLIK zależy od aktywnych metod na koncie handlowca P24. Sklep nie przechowuje danych bankowych ani kodów BLIK — obsługuje je operator płatności.

# 7. Tryb DEMO płatności

Domyślnie w `.env.example`:

```env
P24_ENABLED=false
DEMO_PAYMENT_MODE=true
```

Po złożeniu zamówienia pojawi się przycisk **„Symuluj płatność (DEV)”**. To tylko lokalny test przepływu; nie jest alternatywą dla operatora płatności.

Gdy włączysz realny/sandbox P24, możesz ustawić:

```env
DEMO_PAYMENT_MODE=false
```

# 8. Połączenie z Socratic AI

Ustaw adres istniejącego systemu:

```env
SOCRATIC_AI_URL=http://localhost:8000
```

W nagłówku sklepu jest link „Wróć do Socratic AI”. Z Socratic AI możesz po prostu dodać link do `http://localhost:5000` albo w produkcji do domeny/subdomeny sklepu.

Jeżeli później chcesz **wspólne logowanie (SSO)** między Socratic AI i sklepem, warto zamiast dwóch niezależnych sesji zastosować wspólnego dostawcę OIDC albo podpisany jednorazowy token wejściowy.

# 9. Testy

```bash
pytest -q
```

Testy używają SQLite wyłącznie jako szybkiej bazy in-memory do smoke-testów routingu. Docelowa aplikacja używa MySQL zgodnie z `DATABASE_URL`.

# 10. Co poprawić przed produkcją

- wyłączyć `debug=True` i uruchamiać aplikację za reverse proxy/WSGI,
- użyć HTTPS,
- zmienić `SECRET_KEY` i hasła MySQL,
- wyłączyć `DEMO_PAYMENT_MODE`,
- skonfigurować konta Google/Meta i zweryfikowane redirect URI,
- skonfigurować produkcyjne Przelewy24 i przetestować webhook/verify,
- dodać regulamin, politykę prywatności, dane sprzedawcy i proces zwrotów,
- wdrożyć migracje (np. Alembic/Flask-Migrate) przed dalszą rozbudową schematu,
- opcjonalnie przenieść obrazy produktowe do object storage/CDN.
