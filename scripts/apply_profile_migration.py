from __future__ import annotations

from pathlib import Path
import sys


# When this file is executed directly (python scripts/apply_profile_migration.py),
# Python puts the scripts/ directory on sys.path, not necessarily the project
# root. Bootstrap the Socratic Store root before importing the Flask app.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_text = str(PROJECT_ROOT)
if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)

from sqlalchemy import text

from app import create_app
from app.extensions import db


MIGRATION = Path(__file__).resolve().parent / "migrations" / "20260821_user_dialogue_profiles.sql"
REQUIRED_TABLES = ("user_dialogue_profiles", "user_profile_observations")


def statements(sql: str):
    for block in sql.split(";"):
        statement = block.strip()
        if statement:
            yield statement


def _table_names() -> set[str]:
    return {
        str(row[0])
        for row in db.session.execute(text("SHOW TABLES")).all()
    }


def main() -> None:
    app = create_app()
    sql = MIGRATION.read_text(encoding="utf-8")
    with app.app_context():
        before = _table_names()
        try:
            for statement in statements(sql):
                db.session.execute(text(statement))
            db.session.commit()
            after = _table_names()
            missing = set(REQUIRED_TABLES) - after
            if missing:
                raise RuntimeError(
                    "Profile migration missing tables: "
                    + ", ".join(sorted(missing))
                )
        except Exception:
            db.session.rollback()
            # MySQL DDL can auto-commit. Remove only tables that did not exist
            # before this migration so an interrupted first install is cleanly
            # reversible without touching pre-existing profile data.
            current = _table_names()
            for table_name in reversed(REQUIRED_TABLES):
                if table_name not in before and table_name in current:
                    db.session.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
            db.session.commit()
            raise
    print("Socratic shared dialogue-profile migration: OK")


if __name__ == "__main__":
    main()
