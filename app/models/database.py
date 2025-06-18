import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

# Use a more robust database path for deployment
BASE_DIR = Path(__file__).parent.parent.parent
DATABASE_PATH = BASE_DIR / "data" / "database.db"

# Fallback to current directory if data dir can't be created
if not os.access(BASE_DIR, os.W_OK):
    DATABASE_PATH = Path("database.db")

print(f"Database path configured as: {DATABASE_PATH}")
print(f"Absolute database path: {DATABASE_PATH.absolute()}")


def get_db_connection():
    """Get a database connection"""
    # Ensure the data directory exists
    DATABASE_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def execute_sql_file(sql_file_path: Path) -> None:
    """Execute SQL commands from a file"""
    if sql_file_path.exists():
        with get_db() as conn:
            with open(sql_file_path, "r") as file:
                sql_script = file.read()
                conn.executescript(sql_script)
                conn.commit()
                print(f"Executed SQL file: {sql_file_path}")


def init_db() -> None:
    """Initialize database with SQL files"""
    sql_dir = Path(__file__).parent.parent.parent / "sql"

    # Execute table creation
    create_tables_file = sql_dir / "create_tables.sql"
    if create_tables_file.exists():
        execute_sql_file(create_tables_file)
    else:
        print(f"Warning: {create_tables_file} not found")

    # Execute seed data
    seed_file = sql_dir / "seed_data.sql"
    if seed_file.exists():
        execute_sql_file(seed_file)
    else:
        print(f"Warning: {seed_file} not found")


def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return results"""
    with get_db() as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def execute_insert(query: str, params: tuple = ()) -> Optional[int]:
    """Execute an INSERT query and return the last row id"""
    with get_db() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def execute_update(query: str, params: tuple = ()) -> int:
    """Execute an UPDATE/DELETE query and return affected rows count"""
    with get_db() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount


def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data: total count and recent items"""
    with get_db() as conn:
        # Get total count
        count_result = conn.execute("SELECT COUNT(*) as total FROM items").fetchone()
        total_items = count_result["total"] if count_result else 0

        # Get 10 most recent items
        recent_items_query = """
        SELECT id, name, description, created_at, updated_at
        FROM items
        ORDER BY created_at DESC
        LIMIT 10
        """
        cursor = conn.execute(recent_items_query)
        recent_items = [dict(row) for row in cursor.fetchall()]

        return {
            "total_items": total_items,
            "recent_items": recent_items
        }
