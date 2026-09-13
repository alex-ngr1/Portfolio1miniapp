from __future__ import annotations

import time

from sqlalchemy import create_engine, text

from app.config import settings


def wait_for_db(attempts: int = 30, delay: float = 1.0) -> None:
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3})
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"чекаємо postgres: {exc}")
            time.sleep(delay)
    raise SystemExit(f"База не відповіла: {last_error}")


if __name__ == "__main__":
    wait_for_db()
