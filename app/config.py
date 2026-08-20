import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://socratic_store:change-me@127.0.0.1:3306/socratic_store?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000").rstrip("/")
    SOCRATIC_AI_URL = os.getenv("SOCRATIC_AI_URL", "http://localhost:8000")
    SHOP_NAME = os.getenv("SHOP_NAME", "Socratic Store")
    SHOP_CONTACT_EMAIL = os.getenv("SHOP_CONTACT_EMAIL", "shop@example.local")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    FACEBOOK_GRAPH_VERSION = os.getenv("FACEBOOK_GRAPH_VERSION", "v26.0")

    P24_ENABLED = os.getenv("P24_ENABLED", "false").lower() == "true"
    P24_SANDBOX = os.getenv("P24_SANDBOX", "true").lower() == "true"
    P24_MERCHANT_ID = os.getenv("P24_MERCHANT_ID", "")
    P24_POS_ID = os.getenv("P24_POS_ID", "")
    P24_API_KEY = os.getenv("P24_API_KEY", "")
    P24_CRC = os.getenv("P24_CRC", "")
    DEMO_PAYMENT_MODE = os.getenv("DEMO_PAYMENT_MODE", "true").lower() == "true"
