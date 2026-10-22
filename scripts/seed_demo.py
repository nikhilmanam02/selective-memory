import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import get_db
from app.demo import seed_demo


if __name__ == "__main__":
    with get_db() as connection:
        count = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count:
            raise SystemExit(
                "Database already contains memories. Use POST /api/demo/reset to reset it safely."
            )
        seed_demo(connection)
    print("Loaded the Selective Memory demo memories.")
