#!/usr/bin/env python3
"""
Database management script for the Python API
Usage: python db_manager.py [command]

Commands:
  init    - Initialize the database with tables and seed data
  reset   - Drop all tables and reinitialize
  seed    - Add seed data to existing tables
  query   - Execute a custom SQL query
"""

import sys
import sqlite3
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent))

from app.models.database import init_db, execute_query, execute_sql_file, DATABASE_PATH


def reset_database():
    """Drop all tables and reinitialize"""
    print("Resetting database...")

    # Remove the database file
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
        print("Removed existing database file")

    # Reinitialize
    init_db()
    print("Database reset complete!")


def seed_database():
    """Add seed data to existing tables"""
    sql_dir = Path(__file__).parent / "sql"
    seed_file = sql_dir / "seed_data.sql"

    if seed_file.exists():
        execute_sql_file(seed_file)
        print("Seed data added successfully!")
    else:
        print(f"Seed file not found: {seed_file}")


def interactive_query():
    """Interactive SQL query mode"""
    print("Interactive SQL Query Mode (type 'exit' to quit)")

    while True:
        try:
            query = input("SQL> ").strip()
            if query.lower() == "exit":
                break

            if query:
                if query.upper().startswith("SELECT"):
                    results = execute_query(query)
                    if results:
                        # Print column headers
                        headers = list(results[0].keys())
                        print("\t".join(headers))
                        print("-" * 50)

                        # Print results
                        for row in results:
                            print("\t".join(str(row[col]) for col in headers))
                    else:
                        print("No results found.")
                else:
                    print("Only SELECT queries are supported in interactive mode.")
                    print("Use 'python db_manager.py init' or 'python db_manager.py reset' for modifications.")

        except Exception as e:
            print(f"Error: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "init":
        init_db()
    elif command == "reset":
        reset_database()
    elif command == "seed":
        seed_database()
    elif command == "query":
        interactive_query()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
