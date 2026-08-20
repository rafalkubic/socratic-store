#!/usr/bin/env bash
set -euo pipefail

# Installs a local MySQL server on Debian/Ubuntu and creates the store database/user.
# Usage:
#   MYSQL_APP_PASSWORD='strong-local-password' ./scripts/install_mysql_ubuntu.sh

DB_NAME="${MYSQL_DB_NAME:-socratic_store}"
DB_USER="${MYSQL_DB_USER:-socratic_store}"
DB_PASSWORD="${MYSQL_APP_PASSWORD:-change-me}"

if [[ "$DB_PASSWORD" == "change-me" ]]; then
  echo "WARNING: using development password 'change-me'. Set MYSQL_APP_PASSWORD for anything beyond local testing." >&2
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server
sudo systemctl enable --now mysql

sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "MySQL is ready."
echo "Database: ${DB_NAME}"
echo "User: ${DB_USER}"
echo "DATABASE_URL=mysql+pymysql://${DB_USER}:<PASSWORD>@127.0.0.1:3306/${DB_NAME}?charset=utf8mb4"
