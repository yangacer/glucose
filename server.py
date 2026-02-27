#!/usr/bin/env python3

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import os
import ssl
from collections import defaultdict

PORT = int(os.environ.get('PORT', '8443'))  # Default HTTPS port for mTLS
DB_PATH = os.environ.get('DB_PATH', 'glucose.db')

# mTLS Configuration
MTLS_ENABLED = os.environ.get('MTLS_ENABLED', 'true').lower() == 'true'
CERTS_DIR = os.path.join(os.path.dirname(__file__), 'certs')
CA_CERT_PATH = os.environ.get('CA_CERT', os.path.join(CERTS_DIR, 'ca', 'ca-cert.pem'))
SERVER_CERT_PATH = os.environ.get('SERVER_CERT', os.path.join(CERTS_DIR, 'server', 'server-cert.pem'))
SERVER_KEY_PATH = os.environ.get('SERVER_KEY', os.path.join(CERTS_DIR, 'server', 'server-key.pem'))


# ============================================================================
# Database Helper Functions
# ============================================================================

@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query, params=(), fetch_one=False, commit=False):
    """Execute a query and return results or commit changes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if commit:
            conn.commit()
            result = True
        elif fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        return result


# ============================================================================
# Business Logic Functions
# ============================================================================

def calculate_time_weighted_mean(data):
    """Calculate time-weighted mean using trapezoidal rule."""
    if len(data) < 2:
        return None
    
    total_area = 0.0
    total_time = 0.0
    
    for i in range(1, len(data)):
        t0, v0 = data[i-1]
        t1, v1 = data[i]
        delta_t = (t1 - t0).total_seconds()
        area = (v0 + v1) / 2.0 * delta_t
        total_area += area
        total_time += delta_t
    
    return total_area / total_time if total_time > 0 else None


def calculate_standard_deviation(data):
    """Calculate standard deviation of glucose values."""
    if len(data) < 2:
        return None
    
    values = [v for _, v in data]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def calculate_cv(data):
    """Calculate coefficient of variation (CV) as percentage."""
    if len(data) < 2:
        return None
    
    time_weighted_mean = calculate_time_weighted_mean(data)
    if time_weighted_mean is None or time_weighted_mean == 0:
        return None
    
    std_dev = calculate_standard_deviation(data)
    if std_dev is None:
        return None
    
    return (std_dev / time_weighted_mean) * 100


def generate_cv_windows(end_date, days, window_hours):
    """Generate time windows for CV calculation.
    
    Args:
        end_date: End date (datetime.date)
        days: Number of days to look back
        window_hours: Window size in hours (12, 48, or 120)
    
    Returns:
        List of (window_label, window_start, window_end) tuples
    """
    windows = []
    anchor_time = datetime.combine(end_date, datetime.min.time()) + timedelta(hours=5)
    
    current_window_end = anchor_time
    
    while True:
        window_start = current_window_end - timedelta(hours=window_hours)
        
        days_back = (anchor_time - window_start).total_seconds() / 86400
        if days_back > days:
            break
        
        if window_hours == 12:
            if window_start.hour == 5:
                label = f"{window_start.strftime('%Y-%m-%d')} Day"
            else:
                label = f"{window_start.strftime('%Y-%m-%d')} Night"
        elif window_hours == 48:
            label = f"{window_start.strftime('%Y-%m-%d')} to {current_window_end.strftime('%Y-%m-%d')}"
        else:
            label = f"{window_start.strftime('%Y-%m-%d')} to {current_window_end.strftime('%Y-%m-%d')}"
        
        windows.append((
            label,
            window_start.strftime('%Y-%m-%d %H:%M:%S'),
            current_window_end.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        current_window_end = window_start
    
    return list(reversed(windows))


def calculate_cv_data(glucose_rows, windows):
    """Calculate CV for each time window.
    
    Args:
        glucose_rows: List of (timestamp_str, level) tuples
        windows: List of (label, start, end) tuples
    
    Returns:
        List of {'label': str, 'cv': float} dicts
    """
    result = []
    
    for label, window_start, window_end in windows:
        window_data = []
        for timestamp_str, level in glucose_rows:
            if window_start <= timestamp_str <= window_end:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                window_data.append((dt, level))
        
        cv = calculate_cv(window_data)
        result.append({
            'label': label,
            'cv': round(cv, 2) if cv is not None else None
        })
    
    return result


def calculate_risk_function(glucose_mg_dl):
    """Calculate risk function f(G) for LBGI/HBGI.
    
    Args:
        glucose_mg_dl: Glucose level in mg/dL
    
    Returns:
        Risk function value
    """
    import math
    return 1.509 * (math.log(glucose_mg_dl) ** 1.084 - 5.381)


def calculate_lbgi(data):
    """Calculate Low Blood Glucose Index (LBGI).
    
    Args:
        data: List of (timestamp, glucose_level) tuples
    
    Returns:
        LBGI value or None if insufficient data
    """
    if len(data) < 1:
        return None
    
    low_risks = []
    for _, glucose in data:
        f_g = calculate_risk_function(glucose)
        if f_g < 0:
            rl = 10 * (f_g ** 2)
            low_risks.append(rl)
        else:
            low_risks.append(0)
    
    return sum(low_risks) / len(low_risks) if low_risks else None


def calculate_hbgi(data):
    """Calculate High Blood Glucose Index (HBGI).
    
    Args:
        data: List of (timestamp, glucose_level) tuples
    
    Returns:
        HBGI value or None if insufficient data
    """
    if len(data) < 1:
        return None
    
    high_risks = []
    for _, glucose in data:
        f_g = calculate_risk_function(glucose)
        if f_g > 0:
            rh = 10 * (f_g ** 2)
            high_risks.append(rh)
        else:
            high_risks.append(0)
    
    return sum(high_risks) / len(high_risks) if high_risks else None


def calculate_adrr(glucose_rows, windows):
    """Calculate Average Daily Risk Range (ADRR).
    
    Groups data by calendar days, calculates LBGI + HBGI for each day,
    then averages the daily risk ranges.
    
    Args:
        glucose_rows: List of (timestamp_str, level) tuples
        windows: List of (label, start, end) tuples
    
    Returns:
        ADRR value or None if insufficient data
    """
    if not glucose_rows:
        return None
    
    # Group by calendar date
    daily_data = defaultdict(list)
    for timestamp_str, level in glucose_rows:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        date_key = dt.date()
        daily_data[date_key].append((dt, level))
    
    # Calculate daily risk range for each day
    daily_rr = []
    for date_key in sorted(daily_data.keys()):
        day_data = daily_data[date_key]
        if len(day_data) >= 2:
            lbgi = calculate_lbgi(day_data)
            hbgi = calculate_hbgi(day_data)
            if lbgi is not None and hbgi is not None:
                daily_rr.append(lbgi + hbgi)
    
    return sum(daily_rr) / len(daily_rr) if daily_rr else None


def calculate_risk_metric_data(glucose_rows, windows, metric_type):
    """Calculate LBGI or HBGI for each time window.
    
    Args:
        glucose_rows: List of (timestamp_str, level) tuples
        windows: List of (label, start, end) tuples
        metric_type: 'lbgi' or 'hbgi'
    
    Returns:
        List of {'label': str, 'value': float} dicts
    """
    result = []
    calc_func = calculate_lbgi if metric_type == 'lbgi' else calculate_hbgi
    
    for label, window_start, window_end in windows:
        window_data = []
        for timestamp_str, level in glucose_rows:
            if window_start <= timestamp_str <= window_end:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                window_data.append((dt, level))
        
        value = calc_func(window_data)
        result.append({
            'label': label,
            'value': round(value, 2) if value is not None else None
        })
    
    return result


def calculate_adrr_data(glucose_rows, windows):
    """Calculate ADRR for each time window.
    
    Args:
        glucose_rows: List of (timestamp_str, level) tuples
        windows: List of (label, start, end) tuples
    
    Returns:
        List of {'label': str, 'value': float} dicts
    """
    result = []
    
    for label, window_start, window_end in windows:
        # Filter glucose data for this window
        window_rows = [
            (ts, level) for ts, level in glucose_rows
            if window_start <= ts <= window_end
        ]
        
        # Calculate ADRR for this window (treats window as full period)
        adrr = calculate_adrr(window_rows, [(label, window_start, window_end)])
        result.append({
            'label': label,
            'value': round(adrr, 2) if adrr is not None else None
        })
    
    return result


def calculate_standard_deviation(data):
    """Calculate standard deviation of glucose values."""
    if len(data) < 2:
        return None
    
    values = [v for _, v in data]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def calculate_cv(data):
    """Calculate coefficient of variation (CV) as percentage."""
    if len(data) < 2:
        return None
    
    time_weighted_mean = calculate_time_weighted_mean(data)
    if time_weighted_mean is None or time_weighted_mean == 0:
        return None
    
    std_dev = calculate_standard_deviation(data)
    if std_dev is None:
        return None
    
    return (std_dev / time_weighted_mean) * 100


def calculate_weekly_mean(rows):
    """Group glucose data by week and calculate time-weighted mean."""
    if len(rows) < 2:
        return []
    
    weekly_data = defaultdict(list)
    
    for timestamp_str, level in rows:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        iso_year, iso_week, _ = dt.isocalendar()
        week_key = f'{iso_year}/W{iso_week:02d}'
        weekly_data[week_key].append((dt, level))
    
    result = []
    for week_key in sorted(weekly_data.keys()):
        data = weekly_data[week_key]
        mean = calculate_time_weighted_mean(data)
        if mean is not None:
            result.append({'week': week_key, 'mean': round(mean, 2)})
    
    return result


def calculate_weekly_mean_both(glucose_rows, insulin_rows):
    """Group glucose and insulin data by week and calculate time-weighted mean for both."""
    weekly_glucose = defaultdict(list)
    weekly_insulin = defaultdict(list)
    all_weeks = set()
    
    # Group glucose data by week
    for timestamp_str, level in glucose_rows:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        iso_year, iso_week, _ = dt.isocalendar()
        week_key = f'{iso_year}/W{iso_week:02d}'
        weekly_glucose[week_key].append((dt, level))
        all_weeks.add(week_key)
    
    # Group insulin data by week
    for timestamp_str, level in insulin_rows:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        iso_year, iso_week, _ = dt.isocalendar()
        week_key = f'{iso_year}/W{iso_week:02d}'
        weekly_insulin[week_key].append((dt, level))
        all_weeks.add(week_key)
    
    result = []
    for week_key in sorted(all_weeks):
        glucose_mean = None
        insulin_mean = None
        
        if week_key in weekly_glucose and len(weekly_glucose[week_key]) >= 2:
            glucose_mean = calculate_time_weighted_mean(weekly_glucose[week_key])
        
        if week_key in weekly_insulin and len(weekly_insulin[week_key]) >= 2:
            insulin_mean = calculate_time_weighted_mean(weekly_insulin[week_key])
        
        result.append({
            'week': week_key,
            'glucose_mean': round(glucose_mean, 2) if glucose_mean is not None else None,
            'insulin_mean': round(insulin_mean, 2) if insulin_mean is not None else None
        })
    
    return result


def calculate_standard_deviation(data):
    """Calculate standard deviation of glucose values."""
    if len(data) < 2:
        return None
    
    values = [v for _, v in data]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def calculate_cv(data):
    """Calculate coefficient of variation (CV) as percentage."""
    if len(data) < 2:
        return None
    
    time_weighted_mean = calculate_time_weighted_mean(data)
    if time_weighted_mean is None or time_weighted_mean == 0:
        return None
    
    std_dev = calculate_standard_deviation(data)
    if std_dev is None:
        return None
    
    return (std_dev / time_weighted_mean) * 100


def generate_cv_windows(end_date, days, window_hours):
    """Generate time windows for CV calculation.
    
    Args:
        end_date: End date (datetime.date)
        days: Number of days to look back
        window_hours: Window size in hours (12, 48, or 120)
    
    Returns:
        List of (window_label, window_start, window_end) tuples
    """
    windows = []
    anchor_time = datetime.combine(end_date, datetime.min.time()) + timedelta(hours=5)
    
    current_window_end = anchor_time
    
    while True:
        window_start = current_window_end - timedelta(hours=window_hours)
        
        days_back = (anchor_time - window_start).total_seconds() / 86400
        if days_back > days:
            break
        
        if window_hours == 12:
            if window_start.hour == 5:
                label = f"{window_start.strftime('%Y-%m-%d')} Day"
            else:
                label = f"{window_start.strftime('%Y-%m-%d')} Night"
        elif window_hours == 48:
            label = f"{window_start.strftime('%Y-%m-%d')} to {current_window_end.strftime('%Y-%m-%d')}"
        else:
            label = f"{window_start.strftime('%Y-%m-%d')} to {current_window_end.strftime('%Y-%m-%d')}"
        
        windows.append((
            label,
            window_start.strftime('%Y-%m-%d %H:%M:%S'),
            current_window_end.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        current_window_end = window_start
    
    return list(reversed(windows))


def calculate_cv_data(glucose_rows, windows):
    """Calculate CV for each time window.
    
    Args:
        glucose_rows: List of (timestamp_str, level) tuples
        windows: List of (label, start, end) tuples
    
    Returns:
        List of {'label': str, 'cv': float} dicts
    """
    result = []
    
    for label, window_start, window_end in windows:
        window_data = []
        for timestamp_str, level in glucose_rows:
            if window_start <= timestamp_str <= window_end:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                window_data.append((dt, level))
        
        cv = calculate_cv(window_data)
        result.append({
            'label': label,
            'cv': round(cv, 2) if cv is not None else None
        })
    
    return result


def get_previous_time_window():
    """Calculate previous 12-hour time window."""
    now = datetime.now()
    current_hour = now.hour
    
    if 5 <= current_hour < 17:  # Current is Day (05:00-16:59), previous is Night
        # Previous night window: 17:00 yesterday to 04:59 today
        prev_start = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 17:00:00'
        prev_end = now.strftime('%Y-%m-%d') + ' 04:59:59'
    else:  # Current is Night (17:00-04:59), previous is Day
        if current_hour >= 17:  # Evening (17:00-23:59)
            # Previous day window: 05:00 to 16:59 today
            prev_start = now.strftime('%Y-%m-%d') + ' 05:00:00'
            prev_end = now.strftime('%Y-%m-%d') + ' 16:59:59'
        else:  # Early morning (00:00-04:59)
            # Previous day window: 05:00 to 16:59 yesterday
            prev_start = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 05:00:00'
            prev_end = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 16:59:59'
    
    return prev_start, prev_end


def process_time_window_summary(cursor, window_icon, date_str, window_start, window_end):
    """Process and aggregate data for a 12-hour time window."""
    # Get all intakes in this window
    cursor.execute('''SELECT i.timestamp, i.nutrition_kcal, i.nutrition_amount, n.nutrition_name
                     FROM intake i
                     JOIN nutrition n ON i.nutrition_id = n.id
                     WHERE i.timestamp BETWEEN ? AND ?
                     ORDER BY i.timestamp''',
                  (window_start, window_end))
    intakes = cursor.fetchall()
    
    # Determine reference time for glucose levels
    if intakes:
        # Use first intake time as reference
        first_intake_time = intakes[0][0]
        intake_dt = datetime.strptime(first_intake_time, '%Y-%m-%d %H:%M:%S')
        
        # Aggregate nutrition data
        total_kcal = sum(row[1] for row in intakes)
        nutrition_items = [f"{row[3]} ({row[1]:.1f} kcal)" for row in intakes]
        nutrition_str = ', '.join(nutrition_items)
    else:
        # No intake, use window start as reference
        first_intake_time = None
        intake_dt = datetime.strptime(window_start, '%Y-%m-%d %H:%M:%S')
        total_kcal = 0
        nutrition_str = ''
    
    # Get insulin dose in this window
    cursor.execute('''SELECT timestamp, level FROM insulin
                     WHERE timestamp BETWEEN ? AND ?
                     ORDER BY timestamp DESC LIMIT 1''',
                  (window_start, window_end))
    insulin_row = cursor.fetchone()
    dose_time = insulin_row[0] if insulin_row else None
    dosage = insulin_row[1] if insulin_row else None
    
    # Get glucose levels based on reference time
    glucose_levels = get_glucose_levels_around_intake(cursor, intake_dt.strftime('%Y-%m-%d %H:%M:%S'), intake_dt)
    
    # Get events in window
    cursor.execute('''SELECT event_name FROM event
                     WHERE timestamp BETWEEN ? AND ?
                     ORDER BY timestamp''',
                  (window_start, window_end))
    events = cursor.fetchall()
    grouped_events = ', '.join([e[0] for e in events]) if events else ''
    
    # Get supplements in window
    cursor.execute('''SELECT s.supplement_name, si.supplement_amount 
                     FROM supplement_intake si
                     JOIN supplements s ON si.supplement_id = s.id
                     WHERE si.timestamp BETWEEN ? AND ?
                     ORDER BY si.timestamp''',
                  (window_start, window_end))
    supplements = cursor.fetchall()
    grouped_supplements = ', '.join([f"{s[0]} {s[1]}" for s in supplements]) if supplements else ''
    
    # Check if there's any data in this window
    has_data = intakes or insulin_row or events or supplements
    if not has_data:
        return None
    
    return {
        'am_pm': window_icon,
        'date': date_str,
        'dose_time': dose_time,
        'intake_time': first_intake_time,
        'dosage': dosage,
        'nutrition': nutrition_str,
        'glucose_levels': glucose_levels,
        'kcal_intake': total_kcal,
        'grouped_supplements': grouped_supplements,
        'grouped_events': grouped_events
    }


def get_glucose_levels_around_intake(cursor, first_intake_time, intake_dt):
    """Get glucose levels at and after intake (0 to 11 hours)."""
    glucose_levels = {}
    
    # +0: Most recent glucose before or at intake time
    cursor.execute('''SELECT level FROM glucose
                     WHERE timestamp <= ?
                     ORDER BY timestamp DESC LIMIT 1''',
                  (first_intake_time,))
    zero_row = cursor.fetchone()
    glucose_levels['+0'] = zero_row[0] if zero_row else None
    
    # +1 to +11: Average glucose in ±30min window after intake
    for hour in range(1, 12):
        target_time = intake_dt + timedelta(hours=hour)
        
        # Get average glucose in ±30min window
        window_start_time = (target_time - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        window_end_time = (target_time + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''SELECT AVG(level) FROM glucose
                         WHERE timestamp BETWEEN ? AND ?''',
                      (window_start_time, window_end_time))
        avg_row = cursor.fetchone()
        glucose_levels[f'+{hour}'] = round(avg_row[0], 1) if avg_row[0] else None
    
    return glucose_levels


# ============================================================================
# Data Access Layer - CRUD Operations
# ============================================================================

class DataAccess:
    """Data access layer for database operations."""
    
    @staticmethod
    def create_glucose(timestamp, level):
        execute_query('INSERT INTO glucose (timestamp, level) VALUES (?, ?)',
                     (timestamp, level), commit=True)
    
    @staticmethod
    def create_insulin(timestamp, level):
        execute_query('INSERT INTO insulin (timestamp, level) VALUES (?, ?)',
                     (timestamp, level), commit=True)
    
    @staticmethod
    def create_intake(nutrition_id, timestamp, nutrition_amount):
        kcal_per_gram = execute_query(
            'SELECT kcal_per_gram FROM nutrition WHERE id = ?',
            (nutrition_id,), fetch_one=True)
        
        if not kcal_per_gram:
            raise ValueError('Nutrition not found')
        
        nutrition_kcal = nutrition_amount * kcal_per_gram[0]
        execute_query('''INSERT INTO intake 
                        (nutrition_id, timestamp, nutrition_amount, nutrition_kcal) 
                        VALUES (?, ?, ?, ?)''',
                     (nutrition_id, timestamp, nutrition_amount, nutrition_kcal), commit=True)
        return nutrition_kcal
    
    @staticmethod
    def create_supplement_master(supplement_name, default_amount=1):
        execute_query('''INSERT INTO supplements 
                        (supplement_name, default_amount) 
                        VALUES (?, ?)''',
                     (supplement_name, default_amount), commit=True)
    
    @staticmethod
    def create_supplement_intake(timestamp, supplement_id, supplement_amount):
        execute_query('''INSERT INTO supplement_intake 
                        (timestamp, supplement_id, supplement_amount) 
                        VALUES (?, ?, ?)''',
                     (timestamp, supplement_id, supplement_amount), commit=True)
    
    @staticmethod
    def create_event(timestamp, event_name, event_notes=''):
        execute_query('''INSERT INTO event 
                        (timestamp, event_name, event_notes) 
                        VALUES (?, ?, ?)''',
                     (timestamp, event_name, event_notes), commit=True)
    
    @staticmethod
    def create_nutrition(nutrition_name, kcal, weight):
        execute_query('''INSERT INTO nutrition 
                        (nutrition_name, kcal, weight) 
                        VALUES (?, ?, ?)''',
                     (nutrition_name, kcal, weight), commit=True)
    
    @staticmethod
    def update_glucose(record_id, timestamp, level):
        execute_query('UPDATE glucose SET timestamp = ?, level = ? WHERE id = ?',
                     (timestamp, level, record_id), commit=True)
    
    @staticmethod
    def update_insulin(record_id, timestamp, level):
        execute_query('UPDATE insulin SET timestamp = ?, level = ? WHERE id = ?',
                     (timestamp, level, record_id), commit=True)
    
    @staticmethod
    def update_intake(record_id, nutrition_id, timestamp, nutrition_amount):
        kcal_per_gram = execute_query(
            'SELECT kcal_per_gram FROM nutrition WHERE id = ?',
            (nutrition_id,), fetch_one=True)
        
        if not kcal_per_gram:
            raise ValueError('Nutrition not found')
        
        nutrition_kcal = nutrition_amount * kcal_per_gram[0]
        execute_query('''UPDATE intake 
                        SET timestamp = ?, nutrition_id = ?, nutrition_amount = ?, nutrition_kcal = ?
                        WHERE id = ?''',
                     (timestamp, nutrition_id, nutrition_amount, nutrition_kcal, record_id), commit=True)
    
    @staticmethod
    def update_supplement_master(record_id, supplement_name, default_amount=1):
        execute_query('''UPDATE supplements 
                        SET supplement_name = ?, default_amount = ?
                        WHERE id = ?''',
                     (supplement_name, default_amount, record_id), commit=True)
    
    @staticmethod
    def update_supplement_intake(record_id, timestamp, supplement_id, supplement_amount):
        execute_query('''UPDATE supplement_intake 
                        SET timestamp = ?, supplement_id = ?, supplement_amount = ?
                        WHERE id = ?''',
                     (timestamp, supplement_id, supplement_amount, record_id), commit=True)
    
    @staticmethod
    def update_event(record_id, timestamp, event_name, event_notes=''):
        execute_query('''UPDATE event 
                        SET timestamp = ?, event_name = ?, event_notes = ?
                        WHERE id = ?''',
                     (timestamp, event_name, event_notes, record_id), commit=True)
    
    @staticmethod
    def update_nutrition(record_id, nutrition_name, kcal, weight):
        execute_query('''UPDATE nutrition 
                        SET nutrition_name = ?, kcal = ?, weight = ?
                        WHERE id = ?''',
                     (nutrition_name, kcal, weight, record_id), commit=True)
    
    @staticmethod
    def delete_record(table, record_id):
        execute_query(f'DELETE FROM {table} WHERE id = ?', (record_id,), commit=True)
    
    @staticmethod
    def get_nutrition_list():
        rows = execute_query('SELECT id, nutrition_name, kcal, weight, kcal_per_gram FROM nutrition')
        return [{'id': row[0], 'nutrition_name': row[1], 'kcal': row[2], 
                'weight': row[3], 'kcal_per_gram': row[4]} for row in rows]
    
    @staticmethod
    def get_supplements_list():
        rows = execute_query('SELECT id, supplement_name, default_amount FROM supplements')
        return [{'id': row[0], 'supplement_name': row[1], 'default_amount': row[2]} for row in rows]
    
    @staticmethod
    def get_list_with_filter(query, start_date, end_date, default_hours=24):
        if start_date and end_date:
            rows = execute_query(query, (start_date, end_date + ' 23:59:59'))
        else:
            query = query.replace('BETWEEN ? AND ?', '>= datetime(\'now\', ?)')
            rows = execute_query(query, (f'-{default_hours} hour',))
        return rows


# ============================================================================
# HTTP Request Handler
# ============================================================================

class GlucoseHandler(http.server.SimpleHTTPRequestHandler):
    
    def list_directory(self, path):
        """Redirect root directory to index.html."""
        self.send_response(301)
        self.send_header('Location', '/static/index.html')
        self.end_headers()
        return None
    
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_json(self, data, status=200):
        self._set_headers(status)
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error_json(self, error_msg, status=400):
        self._set_headers(status)
        self.wfile.write(json.dumps({'error': error_msg}).encode())
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def log_message(self, format, *args):
        """Override to add timestamp to request logs"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")
    
    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            query_params = urllib.parse.parse_qs(parsed_path.query)
            
            route_handlers = {
                '/api/nutrition': lambda: self._send_json(DataAccess.get_nutrition_list()),
                '/api/supplements': lambda: self._send_json(DataAccess.get_supplements_list()),
                '/api/intake/previous-window': self.handle_get_previous_window_intake,
                '/api/glucose': lambda: self.handle_get_list('glucose', query_params),
                '/api/insulin': lambda: self.handle_get_list('insulin', query_params),
                '/api/intake': lambda: self.handle_get_intake_list(query_params),
                '/api/supplement-intake': lambda: self.handle_get_supplement_intake_list(query_params),
                '/api/event': lambda: self.handle_get_event_list(query_params),
                '/api/dashboard/glucose-chart': lambda: self.handle_get_glucose_chart(query_params),
                '/api/dashboard/summary': lambda: self.handle_get_summary(query_params),
                '/api/dashboard/cv-charts': lambda: self.handle_get_cv_charts(query_params),
                '/api/dashboard/risk-metrics': lambda: self.handle_get_risk_metrics(query_params),
            }
            
            if path in route_handlers:
                route_handlers[path]()
            else:
                super().do_GET()
        except Exception as e:
            self._send_error_json(f'Server error: {str(e)}', 500)
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e:
            self._send_error_json(f'Invalid JSON: {str(e)}', 400)
            return
        except Exception as e:
            self._send_error_json(f'Request error: {str(e)}', 400)
            return
        
        try:
            if self.path == '/api/glucose':
                DataAccess.create_glucose(data['timestamp'], data['level'])
                self._send_json({'success': True}, 201)
            elif self.path == '/api/insulin':
                DataAccess.create_insulin(data['timestamp'], data['level'])
                self._send_json({'success': True}, 201)
            elif self.path == '/api/intake':
                kcal = DataAccess.create_intake(data['nutrition_id'], data['timestamp'], 
                                                data['nutrition_amount'])
                self._send_json({'success': True, 'nutrition_kcal': kcal}, 201)
            elif self.path == '/api/supplements':
                DataAccess.create_supplement_master(data['supplement_name'], 
                                                    data.get('default_amount', 1))
                self._send_json({'success': True}, 201)
            elif self.path == '/api/supplement-intake':
                DataAccess.create_supplement_intake(data['timestamp'], data['supplement_id'], 
                                                    data['supplement_amount'])
                self._send_json({'success': True}, 201)
            elif self.path == '/api/event':
                DataAccess.create_event(data['timestamp'], data['event_name'], 
                                       data.get('event_notes', ''))
                self._send_json({'success': True}, 201)
            elif self.path == '/api/nutrition':
                DataAccess.create_nutrition(data['nutrition_name'], data['kcal'], data['weight'])
                self._send_json({'success': True}, 201)
            else:
                self._send_error_json('Not found', 404)
        except ValueError as e:
            self._send_error_json(str(e), 400)
        except Exception as e:
            self._send_error_json(f'Server error: {str(e)}', 500)
    
    def do_PUT(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e:
            self._send_error_json(f'Invalid JSON: {str(e)}', 400)
            return
        except Exception as e:
            self._send_error_json(f'Request error: {str(e)}', 400)
            return
        
        try:
            record_id = int(self.path.split('/')[-1])
            
            if '/api/glucose/' in self.path:
                DataAccess.update_glucose(record_id, data['timestamp'], data['level'])
            elif '/api/insulin/' in self.path:
                DataAccess.update_insulin(record_id, data['timestamp'], data['level'])
            elif '/api/intake/' in self.path:
                DataAccess.update_intake(record_id, data['nutrition_id'], 
                                        data['timestamp'], data['nutrition_amount'])
            elif '/api/supplements/' in self.path:
                DataAccess.update_supplement_master(record_id, data['supplement_name'], 
                                                   data.get('default_amount', 1))
            elif '/api/supplement-intake/' in self.path:
                DataAccess.update_supplement_intake(record_id, data['timestamp'], 
                                                   data['supplement_id'], data['supplement_amount'])
            elif '/api/event/' in self.path:
                DataAccess.update_event(record_id, data['timestamp'], data['event_name'], 
                                       data.get('event_notes', ''))
            elif '/api/nutrition/' in self.path:
                DataAccess.update_nutrition(record_id, data['nutrition_name'], 
                                           data['kcal'], data['weight'])
            else:
                self._send_error_json('Not found', 404)
                return
            
            self._send_json({'success': True})
        except ValueError as e:
            self._send_error_json(str(e), 400)
        except Exception as e:
            self._send_error_json(f'Server error: {str(e)}', 500)
    
    def do_DELETE(self):
        try:
            record_id = int(self.path.split('/')[-1])
            
            table_map = {
                '/api/glucose/': 'glucose',
                '/api/insulin/': 'insulin',
                '/api/intake/': 'intake',
                '/api/supplements/': 'supplements',
                '/api/supplement-intake/': 'supplement_intake',
                '/api/event/': 'event',
                '/api/nutrition/': 'nutrition',
            }
            
            table = None
            for prefix, table_name in table_map.items():
                if prefix in self.path:
                    table = table_name
                    break
            
            if table:
                DataAccess.delete_record(table, record_id)
                self._send_json({'success': True})
            else:
                self._send_error_json('Not found', 404)
        except Exception as e:
            self._send_error_json(f'Server error: {str(e)}', 500)
    
    # ========================================================================
    # API Endpoint Handlers
    # ========================================================================
    
    def handle_get_list(self, table, query_params):
        """Generic handler for listing records with date filter."""
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        query = f'''SELECT id, timestamp, level FROM {table} 
                   WHERE timestamp BETWEEN ? AND ? 
                   ORDER BY timestamp DESC'''
        
        rows = DataAccess.get_list_with_filter(query, start_date, end_date)
        records = [{'id': row[0], 'timestamp': row[1], 'level': row[2]} for row in rows]
        self._send_json(records)
    
    def handle_get_intake_list(self, query_params):
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        query = '''SELECT i.id, i.timestamp, i.nutrition_id, n.nutrition_name, 
                         i.nutrition_amount, i.nutrition_kcal
                  FROM intake i
                  JOIN nutrition n ON i.nutrition_id = n.id
                  WHERE i.timestamp BETWEEN ? AND ? 
                  ORDER BY i.timestamp DESC'''
        
        rows = DataAccess.get_list_with_filter(query, start_date, end_date)
        records = [{'id': row[0], 'timestamp': row[1], 'nutrition_id': row[2], 
                   'nutrition_name': row[3], 'nutrition_amount': row[4], 
                   'nutrition_kcal': row[5]} for row in rows]
        self._send_json(records)
    
    def handle_get_supplement_intake_list(self, query_params):
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        query = '''SELECT si.id, si.timestamp, si.supplement_id, s.supplement_name, 
                         si.supplement_amount
                  FROM supplement_intake si
                  JOIN supplements s ON si.supplement_id = s.id
                  WHERE si.timestamp BETWEEN ? AND ? 
                  ORDER BY si.timestamp DESC'''
        
        rows = DataAccess.get_list_with_filter(query, start_date, end_date)
        records = [{'id': row[0], 'timestamp': row[1], 'supplement_id': row[2], 
                   'supplement_name': row[3], 'supplement_amount': row[4]} for row in rows]
        self._send_json(records)
    
    def handle_get_event_list(self, query_params):
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        query = '''SELECT id, timestamp, event_name, event_notes 
                  FROM event 
                  WHERE timestamp BETWEEN ? AND ? 
                  ORDER BY timestamp DESC'''
        
        rows = DataAccess.get_list_with_filter(query, start_date, end_date)
        records = [{'id': row[0], 'timestamp': row[1], 'event_name': row[2], 
                   'event_notes': row[3]} for row in rows]
        self._send_json(records)
    
    def handle_get_previous_window_intake(self):
        prev_start, prev_end = get_previous_time_window()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get intake records
            cursor.execute('''SELECT i.nutrition_id, n.nutrition_name, i.nutrition_amount
                             FROM intake i
                             JOIN nutrition n ON i.nutrition_id = n.id
                             WHERE i.timestamp BETWEEN ? AND ?
                             ORDER BY i.timestamp ASC''',
                          (prev_start, prev_end))
            intake_rows = cursor.fetchall()
            
            # Get supplement intake records
            cursor.execute('''SELECT si.supplement_id, s.supplement_name, si.supplement_amount
                             FROM supplement_intake si
                             JOIN supplements s ON si.supplement_id = s.id
                             WHERE si.timestamp BETWEEN ? AND ?
                             ORDER BY si.timestamp ASC''',
                          (prev_start, prev_end))
            supplement_rows = cursor.fetchall()
        
        intake_records = [{'nutrition_id': row[0], 'nutrition_name': row[1], 
                          'nutrition_amount': row[2]} for row in intake_rows]
        supplement_records = [{'supplement_id': row[0], 'supplement_name': row[1], 
                              'supplement_amount': row[2]} for row in supplement_rows]
        
        self._send_json({
            'nutrition': intake_records,
            'supplements': supplement_records
        })
    
    def handle_get_glucose_chart(self, query_params):
        today = date.today()
        start_date = query_params.get('start_date', [f'{today.year}-01-01'])[0]
        end_date = query_params.get('end_date', [f'{today.year}-12-31'])[0]
        
        glucose_query = '''SELECT timestamp, level FROM glucose 
                          WHERE timestamp BETWEEN ? AND ? 
                          ORDER BY timestamp'''
        
        insulin_query = '''SELECT timestamp, level FROM insulin 
                          WHERE timestamp BETWEEN ? AND ? 
                          ORDER BY timestamp'''
        
        glucose_rows = execute_query(glucose_query, (start_date, end_date + ' 23:59:59'))
        insulin_rows = execute_query(insulin_query, (start_date, end_date + ' 23:59:59'))
        
        weekly_data = calculate_weekly_mean_both(glucose_rows, insulin_rows)
        self._send_json(weekly_data)
    
    def handle_get_summary(self, query_params):
        today = date.today()
        start_date = query_params.get('start_date', [f'{today.year}-{today.month:02d}-01'])[0]
        
        # Calculate last day of current month
        if today.month == 12:
            default_end = f'{today.year}-12-31'
        else:
            next_month = date(today.year, today.month + 1, 1)
            default_end = str(date(next_month.year, next_month.month, 1) - timedelta(days=1))
        
        end_date = query_params.get('end_date', [default_end])[0]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all dates in range
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            summary_data = []
            current_dt = start_dt
            
            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                
                # Process Day window (05:00-16:59)
                day_window_start = f'{date_str} 05:00:00'
                day_window_end = f'{date_str} 16:59:59'
                day_data = process_time_window_summary(cursor, '☀️', date_str, 
                                                     day_window_start, day_window_end)
                if day_data:
                    summary_data.append(day_data)
                
                # Process Night window (17:00 to 04:59 next day)
                night_window_start = f'{date_str} 17:00:00'
                next_day = (current_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                night_window_end = f'{next_day} 04:59:59'
                night_data = process_time_window_summary(cursor, '🌙', date_str, 
                                                     night_window_start, night_window_end)
                if night_data:
                    summary_data.append(night_data)
                
                current_dt += timedelta(days=1)
        
        self._send_json(summary_data)
    
    def handle_get_cv_charts(self, query_params):
        today = date.today()
        end_date_str = query_params.get('end_date', [today.strftime('%Y-%m-%d')])[0]
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Calculate date ranges
        start_7_days = (end_date - timedelta(days=7)).strftime('%Y-%m-%d')
        start_30_days = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date_with_time = end_date_str + ' 23:59:59'
        
        # Query glucose data for 30 days (covers all chart needs)
        glucose_query = '''SELECT timestamp, level FROM glucose 
                          WHERE timestamp BETWEEN ? AND ? 
                          ORDER BY timestamp'''
        glucose_rows = execute_query(glucose_query, (start_30_days, end_date_with_time))
        
        # Generate windows for each chart
        windows_7d_12h = generate_cv_windows(end_date, 7, 12)
        windows_30d_48h = generate_cv_windows(end_date, 30, 48)
        windows_30d_5d = generate_cv_windows(end_date, 30, 120)
        
        # Calculate CV data for each chart
        cv_7d_12h = calculate_cv_data(glucose_rows, windows_7d_12h)
        cv_30d_48h = calculate_cv_data(glucose_rows, windows_30d_48h)
        cv_30d_5d = calculate_cv_data(glucose_rows, windows_30d_5d)
        
        self._send_json({
            'cv_7d_12h': cv_7d_12h,
            'cv_30d_48h': cv_30d_48h,
            'cv_30d_5d': cv_30d_5d
        })
    
    def handle_get_risk_metrics(self, query_params):
        today = date.today()
        end_date_str = query_params.get('end_date', [today.strftime('%Y-%m-%d')])[0]
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Calculate date ranges
        start_7_days = (end_date - timedelta(days=7)).strftime('%Y-%m-%d')
        start_30_days = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date_with_time = end_date_str + ' 23:59:59'
        
        # Query glucose data for 30 days (covers all chart needs)
        glucose_query = '''SELECT timestamp, level FROM glucose 
                          WHERE timestamp BETWEEN ? AND ? 
                          ORDER BY timestamp'''
        glucose_rows = execute_query(glucose_query, (start_30_days, end_date_with_time))
        
        # Generate windows for each chart
        windows_7d_12h = generate_cv_windows(end_date, 7, 12)
        windows_30d_48h = generate_cv_windows(end_date, 30, 48)
        windows_30d_5d = generate_cv_windows(end_date, 30, 120)
        
        # Calculate risk metrics for each chart
        lbgi_7d_12h = calculate_risk_metric_data(glucose_rows, windows_7d_12h, 'lbgi')
        lbgi_30d_48h = calculate_risk_metric_data(glucose_rows, windows_30d_48h, 'lbgi')
        lbgi_30d_5d = calculate_risk_metric_data(glucose_rows, windows_30d_5d, 'lbgi')
        
        hbgi_7d_12h = calculate_risk_metric_data(glucose_rows, windows_7d_12h, 'hbgi')
        hbgi_30d_48h = calculate_risk_metric_data(glucose_rows, windows_30d_48h, 'hbgi')
        hbgi_30d_5d = calculate_risk_metric_data(glucose_rows, windows_30d_5d, 'hbgi')
        
        adrr_7d_12h = calculate_adrr_data(glucose_rows, windows_7d_12h)
        adrr_30d_48h = calculate_adrr_data(glucose_rows, windows_30d_48h)
        adrr_30d_5d = calculate_adrr_data(glucose_rows, windows_30d_5d)
        
        self._send_json({
            'lbgi_7d_12h': lbgi_7d_12h,
            'lbgi_30d_48h': lbgi_30d_48h,
            'lbgi_30d_5d': lbgi_30d_5d,
            'hbgi_7d_12h': hbgi_7d_12h,
            'hbgi_30d_48h': hbgi_30d_48h,
            'hbgi_30d_5d': hbgi_30d_5d,
            'adrr_7d_12h': adrr_7d_12h,
            'adrr_30d_48h': adrr_30d_48h,
            'adrr_30d_5d': adrr_30d_5d
        })


# ============================================================================
# Server Initialization
# ============================================================================

def check_certificate_expiration(cert_path):
    """Check if certificate is expiring soon and log warning."""
    try:
        import subprocess
        result = subprocess.run(
            ['openssl', 'x509', '-in', cert_path, '-noout', '-enddate'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            # Parse expiration date
            date_str = result.stdout.strip().split('=')[1]
            exp_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
            days_left = (exp_date - datetime.now()).days
            
            if days_left < 30:
                print(f"WARNING: Certificate {cert_path} expires in {days_left} days!")
            elif days_left < 0:
                print(f"ERROR: Certificate {cert_path} has EXPIRED!")
    except Exception as e:
        print(f"Could not check certificate expiration: {e}")


def create_ssl_context():
    """Create and configure SSL context for mTLS."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Require client certificates
    context.verify_mode = ssl.CERT_REQUIRED
    
    # Load CA certificate for client verification
    context.load_verify_locations(cafile=CA_CERT_PATH)
    
    # Load server certificate and key
    context.load_cert_chain(certfile=SERVER_CERT_PATH, keyfile=SERVER_KEY_PATH)
    
    # Set minimum TLS version to 1.2
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Configure cipher suites (prefer strong ciphers)
    context.set_ciphers('HIGH:!aNULL:!MD5:!RC4')
    
    print(f"mTLS Configuration:")
    print(f"  CA Certificate: {CA_CERT_PATH}")
    print(f"  Server Certificate: {SERVER_CERT_PATH}")
    print(f"  Server Key: {SERVER_KEY_PATH}")
    
    # Check certificate expiration
    check_certificate_expiration(SERVER_CERT_PATH)
    
    return context


def log_client_certificate(request, client_address):
    """Log client certificate information."""
    try:
        cert = request.getpeercert()
        if cert:
            subject = dict(x[0] for x in cert['subject'])
            cn = subject.get('commonName', 'Unknown')
            print(f"Client connected: {cn} from {client_address[0]}")
        else:
            print(f"Client connected (no cert) from {client_address[0]}")
    except Exception as e:
        print(f"Could not retrieve client certificate: {e}")


class SecureGlucoseHandler(GlucoseHandler):
    """Extended handler that logs client certificate info."""
    
    def setup(self):
        super().setup()
        log_client_certificate(self.request, self.client_address)


def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found. Please run init_db.py first.")
        return
    
    socketserver.TCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    
    if MTLS_ENABLED:
        # Check if certificate files exist
        if not all(os.path.exists(p) for p in [CA_CERT_PATH, SERVER_CERT_PATH, SERVER_KEY_PATH]):
            print("ERROR: mTLS is enabled but certificate files not found!")
            print("Please run ./generate-certs.sh to generate certificates.")
            print("Or set MTLS_ENABLED=false to disable mTLS.")
            return
        
        # Create HTTPS server with mTLS (multi-threaded)
        with socketserver.ThreadingTCPServer(("", PORT), SecureGlucoseHandler) as httpd:
            ssl_context = create_ssl_context()
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
            
            print(f"✓ mTLS enabled - Server running at https://localhost:{PORT}/")
            print(f"  Clients must present valid certificates signed by the CA")
            print(f"  Multi-threaded mode: Handles concurrent requests")
            print(f"  See CLIENT.md for client configuration instructions")
            httpd.serve_forever()
    else:
        # Run without mTLS (development mode, multi-threaded)
        print("WARNING: mTLS is DISABLED - running in insecure mode!")
        print(f"Server running at http://localhost:{PORT}/")
        print(f"Multi-threaded mode: Handles concurrent requests")
        
        with socketserver.ThreadingTCPServer(("", PORT), GlucoseHandler) as httpd:
            httpd.serve_forever()


if __name__ == '__main__':
    main()
