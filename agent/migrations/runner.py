"""Apply pending SQL migrations from this directory.

Tracks applied files in a `schema_migrations` table. Files are applied in
filename-sorted order. Each .sql file is executed as a single transaction.

Usage:
    python migrations/runner.py
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


MIGRATIONS_DIR = Path(__file__).parent
TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) NOT NULL PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""".strip()


def _split_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for raw_line in sql.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(raw_line)
        if stripped.endswith(";"):
            joined = "\n".join(buffer).rstrip().rstrip(";").strip()
            if joined:
                statements.append(joined)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail.rstrip(";"))
    return statements


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️  DATABASE_URL not set, skipping migrations", file=sys.stderr)
        return 0

    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("ℹ️  no .sql migrations found")
        return 0

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text(TRACKING_DDL))

    # Hold a MySQL advisory lock so concurrent containers don't race.
    with engine.connect() as lock_conn:
        got = lock_conn.execute(
            text("SELECT GET_LOCK('stochips_migrations', 60)")
        ).scalar()
        if got != 1:
            print("⚠️  could not acquire migration lock, skipping", file=sys.stderr)
            return 0
        try:
            applied = {
                row[0]
                for row in lock_conn.execute(
                    text("SELECT filename FROM schema_migrations")
                )
            }
            pending = [p for p in files if p.name not in applied]
            if not pending:
                print(f"✅ migrations up to date ({len(applied)} applied)")
                return 0

            for path in pending:
                print(f"▶️  applying migration {path.name}")
                sql = path.read_text(encoding="utf-8")
                statements = _split_statements(sql)
                try:
                    with engine.begin() as conn:
                        for stmt in statements:
                            conn.execute(text(stmt))
                        conn.execute(
                            text(
                                "INSERT INTO schema_migrations (filename) VALUES (:f)"
                            ),
                            {"f": path.name},
                        )
                except Exception as exc:
                    print(
                        f"❌ migration {path.name} failed: {exc}", file=sys.stderr
                    )
                    return 1
                print(f"✅ applied {path.name}")

            print(f"✅ {len(pending)} migration(s) applied")
            return 0
        finally:
            lock_conn.execute(text("SELECT RELEASE_LOCK('stochips_migrations')"))


if __name__ == "__main__":
    sys.exit(main())
