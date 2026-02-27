#!/usr/bin/env python3

import sqlite3
import os

DB_PATH = 'glucose.db'


def create_schema(conn):
    """
    Create database schema with tables and indexes.
    Single source of truth for schema definition.
    
    Args:
        conn: SQLite database connection
    """
    cursor = conn.cursor()
    
    # Create glucose table
    cursor.execute('''
    CREATE TABLE glucose (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level INTEGER NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX idx_glucose_timestamp ON glucose(timestamp)')
    
    # Create insulin table
    cursor.execute('''
    CREATE TABLE insulin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level REAL NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX idx_insulin_timestamp ON insulin(timestamp)')
    
    # Create nutrition table
    cursor.execute('''
    CREATE TABLE nutrition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nutrition_name TEXT NOT NULL,
        kcal REAL NOT NULL,
        weight REAL NOT NULL,
        kcal_per_gram REAL GENERATED ALWAYS AS (kcal / weight) STORED
    )
    ''')
    
    # Create intake table
    cursor.execute('''
    CREATE TABLE intake (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nutrition_id INTEGER REFERENCES nutrition(id),
        timestamp DATETIME NOT NULL,
        nutrition_amount REAL NOT NULL,
        nutrition_kcal REAL NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX idx_intake_timestamp ON intake(timestamp)')
    cursor.execute('CREATE INDEX idx_intake_nutrition_id ON intake(nutrition_id)')
    
    # Create supplements table (master)
    cursor.execute('''
    CREATE TABLE supplements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplement_name TEXT NOT NULL,
        default_amount REAL NOT NULL DEFAULT 1
    )
    ''')
    
    # Create supplement_intake table
    cursor.execute('''
    CREATE TABLE supplement_intake (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        supplement_id INTEGER REFERENCES supplements(id),
        supplement_amount REAL NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX idx_supplement_intake_timestamp ON supplement_intake(timestamp)')
    cursor.execute('CREATE INDEX idx_supplement_intake_supplement_id ON supplement_intake(supplement_id)')
    
    # Create event table
    cursor.execute('''
    CREATE TABLE event (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        event_name TEXT NOT NULL,
        event_notes TEXT
    )
    ''')
    cursor.execute('CREATE INDEX idx_event_timestamp ON event(timestamp)')
    
    conn.commit()


def init_database():
    """Initialize production database if it doesn't exist"""
    if os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} already exists. Skipping creation.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    conn.close()
    
    print(f"Database {DB_PATH} created successfully!")


if __name__ == '__main__':
    init_database()
