from sqlalchemy import text
from sqlalchemy.orm import Session

_UPDATES = (
    ("users", "role", {"OWNER": "owner", "WORKER": "worker"}),
    ("tasks", "status", {"OPEN": "open", "AWAITING_REVIEW": "awaiting_review", "CLOSED": "closed"}),
    ("evidence_files", "kind", {"PHOTO": "photo", "VIDEO": "video"}),
)


def normalize_enum_values(db: Session) -> None:
    """Rewrite leftover NAME rows (OWNER) to values (owner). Safe to run repeatedly."""
    for table, column, mapping in _UPDATES:
        for old, new in mapping.items():
            db.execute(
                text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old"),
                {"new": new, "old": old},
            )
    db.commit()
