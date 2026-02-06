#!/usr/bin/env python3

import sqlite3
import os

DB_PATH = 'glucose.db'

def init_database():
    if os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} already exists. Skipping creation.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create glucose table
    cursor.execute('''
    CREATE TABLE glucose (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level INTEGER NOT NULL
    )
    ''')
    
    # Create insulin table
    cursor.execute('''
    CREATE TABLE insulin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level REAL NOT NULL
    )
    ''')
    
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
    
    # Create supplements table
    cursor.execute('''
    CREATE TABLE supplements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        supplement_name TEXT NOT NULL,
        supplement_amount REAL NOT NULL
    )
    ''')
    
    # Create event table
    cursor.execute('''
    CREATE TABLE event (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        event_name TEXT NOT NULL,
        event_notes TEXT
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX idx_glucose_timestamp ON glucose(timestamp)')
    cursor.execute('CREATE INDEX idx_insulin_timestamp ON insulin(timestamp)')
    cursor.execute('CREATE INDEX idx_intake_timestamp ON intake(timestamp)')
    cursor.execute('CREATE INDEX idx_intake_nutrition_id ON intake(nutrition_id)')
    cursor.execute('CREATE INDEX idx_supplements_timestamp ON supplements(timestamp)')
    cursor.execute('CREATE INDEX idx_event_timestamp ON event(timestamp)')
    
    conn.commit()
    conn.close()
    
    print(f"Database {DB_PATH} created successfully!")

if __name__ == '__main__':
    init_database()
