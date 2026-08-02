"""
Truncate training-session data in the e2e database.

Run from backend/: E2E_DATABASE_URL=... python -m scripts.reset_e2e_db

Playwright's globalSetup calls this before every suite run. Without it each run
leaves its logged sets behind, and since WEEKLY_SET_LIMIT caps a muscle group at
20 sets per ISO week, after roughly ten runs the volume filter starts (correctly)
rejecting the partner suggestion and the suite fails for a reason that has
nothing to do with the code under test.

Only the four session tables are cleared. The pattern taxonomy
(`movement_patterns`, `exercise_pattern_map`), the exercise catalogue, and the
seeded staple pool must survive: the suite depends on them and re-seeding them
per run would be both slow and fragile.

Refuses to touch anything unless E2E_DATABASE_URL names a database with "e2e" in
its name, so a stray DATABASE_URL cannot point this at a real database.
"""

import asyncio
import os
import sys
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Ordered children-first; every table with an FK into the set is present, so no
# CASCADE is needed (and none is used - CASCADE would silently truncate tables
# added later that reference these).
SESSION_TABLES = ("entry_sets", "round_entries", "superset_rounds", "training_sessions")


def target_url() -> str:
    """Return the e2e connection string, or exit if it is missing/unsafe."""
    url = os.environ.get("E2E_DATABASE_URL", "").strip()
    if not url:
        sys.exit("E2E_DATABASE_URL is not set. Refusing to truncate any database.")
    db_name = urlparse(url).path.lstrip("/")
    if "e2e" not in db_name.lower():
        sys.exit(
            f"E2E_DATABASE_URL points at database {db_name!r}, whose name does not "
            "contain 'e2e'. Refusing to truncate it."
        )
    return url


async def main() -> None:
    url = target_url()
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(f"TRUNCATE TABLE {', '.join(SESSION_TABLES)} RESTART IDENTITY")
            )
    finally:
        await engine.dispose()
    print(f"e2e session tables truncated: {', '.join(SESSION_TABLES)}")


if __name__ == "__main__":
    asyncio.run(main())
