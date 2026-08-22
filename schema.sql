-- Socratic Store relational schema for MySQL 8.x.
-- Database/user creation is handled by scripts/install_mysql_ubuntu.sh or docker-compose.yml.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NULL,
    display_name VARCHAR(160) NULL,
    preferred_language VARCHAR(2) NOT NULL DEFAULT 'pl',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_users_email (email),
    INDEX ix_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider VARCHAR(32) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_oauth_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_oauth_provider_user UNIQUE (provider, provider_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_dialogue_profiles (
    user_id INT PRIMARY KEY,
    hylik_weight DECIMAL(8,6) NOT NULL DEFAULT 0.333333,
    psychik_weight DECIMAL(8,6) NOT NULL DEFAULT 0.333333,
    pneumatyk_weight DECIMAL(8,6) NOT NULL DEFAULT 0.333334,
    dominant_profile VARCHAR(16) NOT NULL DEFAULT 'neutral',
    confidence DECIMAL(8,6) NOT NULL DEFAULT 0.000000,
    sample_count INT NOT NULL DEFAULT 0,
    profiling_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_conversation_id VARCHAR(128) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_dialogue_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_profile_observations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    conversation_id VARCHAR(128) NULL,
    sample_number INT NOT NULL,
    hylik_evidence DECIMAL(8,6) NOT NULL,
    psychik_evidence DECIMAL(8,6) NOT NULL,
    pneumatyk_evidence DECIMAL(8,6) NOT NULL,
    evidence_strength DECIMAL(8,6) NOT NULL,
    resulting_dominant_profile VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_profile_observation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX ix_profile_observation_user (user_id),
    INDEX ix_profile_observation_conversation (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(50) NOT NULL UNIQUE,
    name_pl VARCHAR(120) NOT NULL,
    name_en VARCHAR(120) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    sku VARCHAR(64) NOT NULL UNIQUE,
    slug VARCHAR(120) NOT NULL UNIQUE,
    name_pl VARCHAR(200) NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    description_pl TEXT NOT NULL,
    description_en TEXT NOT NULL,
    price_pln DECIMAL(10,2) NOT NULL,
    stock_qty INT NOT NULL DEFAULT 0,
    image_path VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES categories(id),
    INDEX ix_products_category (category_id),
    INDEX ix_products_sku (sku),
    INDEX ix_products_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    public_id VARCHAR(36) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'payment_pending',
    currency VARCHAR(3) NOT NULL DEFAULT 'PLN',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_provider VARCHAR(40) NOT NULL DEFAULT 'przelewy24',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME NULL,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX ix_orders_user (user_id),
    INDEX ix_orders_status (status),
    INDEX ix_orders_public_id (public_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NULL,
    sku VARCHAR(64) NOT NULL,
    name VARCHAR(200) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id),
    INDEX ix_order_items_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payment_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    provider VARCHAR(40) NOT NULL,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    provider_order_id VARCHAR(100) NULL,
    token VARCHAR(255) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'created',
    raw_response TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    INDEX ix_payment_order (order_id),
    INDEX ix_payment_status (status),
    INDEX ix_payment_provider_order (provider_order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
