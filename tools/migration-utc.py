#!/usr/bin/env python3
"""
migration-utc.py — Convert stored local timestamps to UTC.

Usage:
    python3 migration-utc.py --db glucose.db --from-tz Asia/Taipei
    python3 migration-utc.py --db glucose.db --from-tz Asia/Taipei --apply

Options:
    --db         Path to SQLite database file (required)
    --from-tz    IANA timezone name the data was recorded in (required)
    --apply      Write changes to the database (default: dry run)
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MIGRATION_ID = "utc-migration-v1"
TABLES = ["glucose", "insulin", "intake", "supplement_intake", "event"]
FMT = "%Y-%m-%d %H:%M:%S"


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL,
            from_tz TEXT NOT NULL,
            rows_converted INTEGER NOT NULL
        )
    """)
    conn.commit()


def already_applied(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT id, applied_at, from_tz, rows_converted FROM _migrations WHERE id = ?",
        (MIGRATION_ID,),
    ).fetchone()
    if row:
        print(
            f"Migration '{MIGRATION_ID}' was already applied on {row[1]} "
            f"(from_tz={row[2]}, {row[3]} rows converted). Aborting."
        )
        return True
    return False


def convert_timestamp(ts: str, src_tz: ZoneInfo) -> str:
    """Parse a naive local timestamp string and return it as UTC string."""
    naive = datetime.strptime(ts, FMT)
    local = naive.replace(tzinfo=src_tz)
    utc = local.astimezone(timezone.utc)
    return utc.strftime(FMT)


def migrate(db_path: str, from_tz_name: str, apply: bool) -> None:
    try:
        src_tz = ZoneInfo(from_tz_name)
    except ZoneInfoNotFoundError:
        print(f"Error: unknown timezone '{from_tz_name}'.")
        print("Install tzdata if needed: pip install tzdata")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    ensure_migrations_table(conn)

    if apply and already_applied(conn):
        conn.close()
        sys.exit(1)

    total_converted = 0

    for table in TABLES:
        rows = conn.execute(f"SELECT id, timestamp FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: no rows")
            continue

        updates = []
        for row in rows:
            utc_ts = convert_timestamp(row["timestamp"], src_tz)
            updates.append((utc_ts, row["id"]))

        # Show sample for dry run
        sample = rows[0]
        sample_utc = convert_timestamp(sample["timestamp"], src_tz)
        print(
            f"  {table}: {len(updates)} rows  "
            f"(e.g. '{sample['timestamp']}' → '{sample_utc}')"
        )

        if apply:
            conn.executemany(
                f"UPDATE {table} SET timestamp = ? WHERE id = ?", updates
            )

        total_converted += len(updates)

    if apply:
        conn.execute(
            "INSERT INTO _migrations (id, applied_at, from_tz, rows_converted) "
            "VALUES (?, ?, ?, ?)",
            (
                MIGRATION_ID,
                datetime.now(timezone.utc).strftime(FMT),
                from_tz_name,
                total_converted,
            ),
        )
        conn.commit()
        print(f"\nApplied. {total_converted} rows converted from {from_tz_name} to UTC.")
    else:
        print(f"\nDry run complete. {total_converted} rows would be converted.")
        print("Re-run with --apply to write changes.")

    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", required=True, help="Path to SQLite database file")
    parser.add_argument("--from-tz", required=True, help="IANA source timezone (e.g. Asia/Taipei)")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    mode = "APPLYING" if args.apply else "DRY RUN"
    print(f"[{mode}] {args.db}  |  source timezone: {args.from_tz}\n")

    migrate(args.db, args.from_tz, args.apply)


if __name__ == "__main__":
    main()
