#!/usr/bin/env python3
import sqlite3
import csv
from datetime import datetime

def parse_timestamp(ts_str):
    """Parse timestamp from CSV format to SQLite format"""
    ts_str = ts_str.strip()
    try:
        dt = datetime.strptime(ts_str, '%Y/%m/%d  %H:%M:%S')
    except ValueError:
        dt = datetime.strptime(ts_str, '%Y/%m/%d %H:%M:%S')
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def import_glucose(conn, csv_file):
    """Import glucose data from CSV"""
    cursor = conn.cursor()
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            timestamp = parse_timestamp(row['timestamp'])
            level = int(row['level'])
            cursor.execute(
                'INSERT INTO glucose (timestamp, level) VALUES (?, ?)',
                (timestamp, level)
            )
            count += 1
    conn.commit()
    print(f"Imported {count} glucose records")

def import_insulin(conn, csv_file):
    """Import insulin data from CSV"""
    cursor = conn.cursor()
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            timestamp = parse_timestamp(row['timestamp'])
            level = float(row['level'])
            cursor.execute(
                'INSERT INTO insulin (timestamp, level) VALUES (?, ?)',
                (timestamp, level)
            )
            count += 1
    conn.commit()
    print(f"Imported {count} insulin records")

if __name__ == '__main__':
    conn = sqlite3.connect('glucose.db')
    
    print("Importing glucose.csv...")
    import_glucose(conn, 'glucose.csv')
    
    print("Importing insulin.csv...")
    import_insulin(conn, 'insulin.csv')
    
    conn.close()
    print("Import completed successfully!")
