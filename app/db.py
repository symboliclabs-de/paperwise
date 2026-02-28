import aiosqlite

from app.config import settings
from app.models import DocumentStatus, Result

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


async def init() -> None:
    """Initializes the database"""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(_CREATE_TABLE)
        await db.commit()


async def save_document(result: Result) -> str:
    """Saves a document to the database"""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO documents (document_id, status, data, created_at) VALUES (?, ?, ?, ?)",
            (
                result.document_id,
                result.status.value,
                result.model_dump_json(),
                result.created_at.isoformat(),
            ),
        )
        await db.commit()
    return result.document_id


async def get_document(document_id: str) -> Result | None:
    """Returns the document with the provided id"""
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            "SELECT data FROM documents WHERE document_id = ?", (document_id,)
        )
        row = await cursor.fetchone()
    if not row:
        return None
    return Result.model_validate_json(row[0])


async def get_documents_by_status(*statuses: DocumentStatus) -> list[Result]:
    """Returns a list of documents matching the provided statuses"""
    if not statuses:
        return []
    placeholders = ",".join("?" for _ in statuses)
    values = tuple(status.value for status in statuses)
    async with aiosqlite.connect(settings.db_path) as db:
        cursor = await db.execute(
            f"SELECT data FROM documents WHERE status IN ({placeholders}) ORDER BY created_at DESC",
            values,
        )
        rows = await cursor.fetchall()
    return [Result.model_validate_json(row[0]) for row in rows]
