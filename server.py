#!/usr/bin/env python3

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import math
import queue
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta, timezone, time as dt_time
from contextlib import contextmanager
from zoneinfo import ZoneInfo
import os
import ssl
from collections import defaultdict

PORT = int(os.environ.get('PORT', '8443'))  # Default HTTPS port for mTLS
DB_PATH = os.environ.get('DB_PATH', 'glucose.db')
DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '5'))
MAX_BODY_BYTES = int(os.environ.get('MAX_BODY_BYTES', str(64 * 1024)))  # 64 KB
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '20'))
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))  # seconds

DEBUG_STATIC = os.environ.get('DEBUG_STATIC', 'false').lower() == 'true'

# Logging — all output (requests, errors, startup) unified on stdout
class _CompactFormatter(logging.Formatter):
    converter = time.gmtime  # use UTC, not local time
    _ABBREV = {
        logging.DEBUG:    'D',
        logging.INFO:     'I',
        logging.WARNING:  'W',
        logging.ERROR:    'E',
        logging.CRITICAL: 'C',
    }

    def format(self, record):
        record.levelname = self._ABBREV.get(record.levelno, record.levelname[0])
        return super().format(record)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_CompactFormatter(
    fmt='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
))
logging.basicConfig(
    handlers=[_handler],
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO),
)
logger = logging.getLogger(__name__)
logger.info("All timestamps are UTC")

# mTLS Configuration
MTLS_ENABLED = os.environ.get('MTLS_ENABLED', 'true').lower() == 'true'
CERTS_DIR = os.path.join(os.path.dirname(__file__), 'certs')
CA_CERT_PATH = os.environ.get('CA_CERT', os.path.join(CERTS_DIR, 'ca', 'ca-cert.pem'))
SERVER_CERT_PATH = os.environ.get('SERVER_CERT', os.path.join(CERTS_DIR, 'server', 'server-cert.pem'))
SERVER_KEY_PATH = os.environ.get('SERVER_KEY', os.path.join(CERTS_DIR, 'server', 'server-key.pem'))


# ============================================================================
# Database Connection Pool
# ============================================================================

class ConnectionPool:
    """
    Fixed-size SQLite connection pool backed by a Queue.

    Connections are created once at startup and reused across requests.
    check_same_thread=False is required because ThreadingTCPServer hands
    the same connection object to different threads over time (never
    concurrently — the Queue ensures exclusive access per checkout).
    """

    def __init__(self, db_path, size, timeout=30):
        self._db_path = db_path
        self._timeout = timeout
        self._pool = queue.Queue(maxsize=size)
        for _ in range(size):
            self._pool.put(self._new_connection())

    def _new_connection(self):
        return sqlite3.connect(self._db_path, timeout=self._timeout, check_same_thread=False)

    @contextmanager
    def connection(self):
        try:
            conn = self._pool.get(timeout=self._timeout)
        except queue.Empty:
            raise RuntimeError('Database connection pool exhausted')
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.put(conn)


_db_pool: ConnectionPool | None = None


@contextmanager
def get_db_connection():
    """Borrow a connection from the pool; return it automatically on exit."""
    with _db_pool.connection() as conn:
        yield conn


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
# Timezone Helpers
# ============================================================================

def parse_tz(query_params: dict, required: bool = True) -> str:
    """Extract and validate an IANA timezone name from query params."""
    tz_values = query_params.get('tz', [])
    if not tz_values or not tz_values[0]:
        if required:
            raise ValueError("Missing required 'tz' parameter")
        return 'UTC'
    try:
        ZoneInfo(tz_values[0])
        return tz_values[0]
    except Exception:
        raise ValueError(f"Invalid timezone: '{tz_values[0]}'")


def to_utc_range(date_str: str, tz_name: str) -> tuple:
    """Convert a local YYYY-MM-DD to a UTC (start_inclusive, end_exclusive) string pair."""
    tz = ZoneInfo(tz_name)
    parts = [int(p) for p in date_str.split('-')]
    local_start = datetime(*parts, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    fmt = '%Y-%m-%d %H:%M:%S'
    return (
        local_start.astimezone(timezone.utc).strftime(fmt),
        local_end.astimezone(timezone.utc).strftime(fmt),
    )


def local_5am_utc(d: date, tz_name: str) -> datetime:
    """Return 5:00 AM local time on date d as a UTC-aware datetime."""
    tz = ZoneInfo(tz_name)
    return datetime.combine(d, dt_time(5, 0), tzinfo=tz).astimezone(timezone.utc)


def today_in_tz(tz_name: str) -> date:
    """Return today's date in the given client timezone."""
    return datetime.now(timezone.utc).astimezone(ZoneInfo(tz_name)).date()


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

    risk_scores = []
    for _, glucose in data:
        risk_score = calculate_risk_function(glucose)
        if risk_score < 0:
            low_risk = 10 * (risk_score ** 2)
            risk_scores.append(low_risk)
        else:
            risk_scores.append(0)

    return sum(risk_scores) / len(risk_scores) if risk_scores else None


def calculate_hbgi(data):
    """Calculate High Blood Glucose Index (HBGI).

    Args:
        data: List of (timestamp, glucose_level) tuples

    Returns:
        HBGI value or None if insufficient data
    """
    if len(data) < 1:
        return None

    risk_scores = []
    for _, glucose in data:
        risk_score = calculate_risk_function(glucose)
        if risk_score > 0:
            high_risk = 10 * (risk_score ** 2)
            risk_scores.append(high_risk)
        else:
            risk_scores.append(0)

    return sum(risk_scores) / len(risk_scores) if risk_scores else None


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
    daily_risk_ranges = []
    for date_key in sorted(daily_data.keys()):
        day_data = daily_data[date_key]
        if len(day_data) >= 2:
            lbgi = calculate_lbgi(day_data)
            hbgi = calculate_hbgi(day_data)
            if lbgi is not None and hbgi is not None:
                daily_risk_ranges.append(lbgi + hbgi)

    return sum(daily_risk_ranges) / len(daily_risk_ranges) if daily_risk_ranges else None


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
    metric_calculator = calculate_lbgi if metric_type == 'lbgi' else calculate_hbgi

    for label, window_start, window_end in windows:
        window_data = []
        for timestamp_str, level in glucose_rows:
            if window_start <= timestamp_str <= window_end:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                window_data.append((dt, level))

        value = metric_calculator(window_data)
        result.append({
            'label': label,
            'value': round(value, 2) if value is not None else None
        })

    return result


def calculate_adrr_data(glucose_rows, windows):
    """Calculate ADRR for each time window.

    ADRR per window = LBGI + HBGI computed directly on that window's readings.
    This mirrors how calculate_lbgi/hbgi work and avoids incorrect UTC date-grouping
    for sub-day windows that cross UTC midnight.

    Args:
        glucose_rows: List of (timestamp_str, level) tuples
        windows: List of (label, start, end) tuples

    Returns:
        List of {'label': str, 'value': float} dicts
    """
    result = []

    for label, window_start, window_end in windows:
        window_data = [
            (datetime.strptime(ts, '%Y-%m-%d %H:%M:%S'), level)
            for ts, level in glucose_rows
            if window_start <= ts <= window_end
        ]

        lbgi = calculate_lbgi(window_data)
        hbgi = calculate_hbgi(window_data)
        adrr = (lbgi + hbgi) if (lbgi is not None and hbgi is not None) else None
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


def generate_cv_windows(end_date, days, window_hours, tz_name):
    """Generate time windows for CV calculation.

    Args:
        end_date: End date (datetime.date) in the client's local timezone
        days: Number of days to look back
        window_hours: Window size in hours (12, 48, or 120)
        tz_name: IANA timezone name of the client

    Returns:
        List of (window_label, window_start_utc, window_end_utc) tuples
    """
    windows = []
    anchor_time = local_5am_utc(end_date, tz_name)

    current_window_end = anchor_time

    while True:
        window_start = current_window_end - timedelta(hours=window_hours)

        days_back = (anchor_time - window_start).total_seconds() / 86400
        if days_back > days:
            break

        if window_hours == 12:
            local_start = window_start.astimezone(ZoneInfo(tz_name))
            if local_start.hour == 5:
                label = f"{local_start.strftime('%Y-%m-%d')} Day"
            else:
                label = f"{local_start.strftime('%Y-%m-%d')} Night"
        else:
            local_start = window_start.astimezone(ZoneInfo(tz_name))
            local_end = current_window_end.astimezone(ZoneInfo(tz_name))
            label = f"{local_start.strftime('%Y-%m-%d')} to {local_end.strftime('%Y-%m-%d')}"

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


def get_previous_time_window(tz_name: str) -> tuple:
    """Calculate previous 12-hour time window in UTC for the given client timezone."""
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(timezone.utc).astimezone(tz)
    current_hour = now_local.hour
    fmt = '%Y-%m-%d %H:%M:%S'

    def to_utc_str(dt_local):
        return dt_local.astimezone(timezone.utc).strftime(fmt)

    if 5 <= current_hour < 17:  # Current is Day (05:00-16:59), previous is Night
        # Previous night: 17:00 yesterday to 04:59:59 today (local)
        prev_start_local = now_local.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
        prev_end_local = now_local.replace(hour=4, minute=59, second=59, microsecond=0)
    elif current_hour >= 17:  # Evening (17:00-23:59), previous is Day
        # Previous day: 05:00 to 16:59:59 today (local)
        prev_start_local = now_local.replace(hour=5, minute=0, second=0, microsecond=0)
        prev_end_local = now_local.replace(hour=16, minute=59, second=59, microsecond=0)
    else:  # Early morning (00:00-04:59), previous is Day yesterday
        yesterday = now_local - timedelta(days=1)
        prev_start_local = yesterday.replace(hour=5, minute=0, second=0, microsecond=0)
        prev_end_local = yesterday.replace(hour=16, minute=59, second=59, microsecond=0)

    return to_utc_str(prev_start_local), to_utc_str(prev_end_local)


def process_time_window_summary(cursor, window_icon, date_str, window_start, window_end):
    """Process and aggregate data for a 12-hour time window."""
    # Get all intakes in this window (half-open: [window_start, window_end))
    cursor.execute('''SELECT i.timestamp, i.nutrition_kcal, n.nutrition_name
                     FROM intake i
                     JOIN nutrition n ON i.nutrition_id = n.id
                     WHERE i.timestamp >= ? AND i.timestamp < ?
                     ORDER BY i.timestamp''',
                  (window_start, window_end))
    intakes = cursor.fetchall()

    # Always use window_start as reference time for glucose levels
    window_start_dt = datetime.strptime(window_start, '%Y-%m-%d %H:%M:%S')

    if intakes:
        first_intake_time = intakes[0][0]

        # Aggregate nutrition data
        total_kcal = sum(row[1] for row in intakes)
        nutrition_items = [f"{row[2]} ({row[1]:.1f} kcal)" for row in intakes]
        nutrition_str = ', '.join(nutrition_items)
    else:
        first_intake_time = None
        total_kcal = 0
        nutrition_str = ''

    # Get insulin dose in this window (half-open: [window_start, window_end))
    cursor.execute('''SELECT timestamp, level FROM insulin
                     WHERE timestamp >= ? AND timestamp < ?
                     ORDER BY timestamp DESC LIMIT 1''',
                  (window_start, window_end))
    insulin_row = cursor.fetchone()
    dose_time = insulin_row[0] if insulin_row else None
    dosage = insulin_row[1] if insulin_row else None

    # Get glucose levels based on window start time
    glucose_levels = get_glucose_levels_from_window_start(cursor, window_start_dt)

    # Get events in window (half-open: [window_start, window_end))
    cursor.execute('''SELECT event_name FROM event
                     WHERE timestamp >= ? AND timestamp < ?
                     ORDER BY timestamp''',
                  (window_start, window_end))
    events = cursor.fetchall()
    grouped_events = ', '.join([e[0] for e in events]) if events else ''

    # Get supplements in window (half-open: [window_start, window_end))
    cursor.execute('''SELECT s.supplement_name, si.supplement_amount
                     FROM supplement_intake si
                     JOIN supplements s ON si.supplement_id = s.id
                     WHERE si.timestamp >= ? AND si.timestamp < ?
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


def get_glucose_levels_from_window_start(cursor, window_start_dt):
    """Get average glucose levels in each 1-hour bucket from window start (0 to 11 hours)."""
    glucose_levels = {}

    for hour in range(12):
        bucket_start = (window_start_dt + timedelta(hours=hour)).strftime('%Y-%m-%d %H:%M:%S')
        bucket_end = (window_start_dt + timedelta(hours=hour + 1)).strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''SELECT AVG(level) FROM glucose
                         WHERE timestamp >= ? AND timestamp < ?''',
                      (bucket_start, bucket_end))
        avg_row = cursor.fetchone()
        glucose_levels[f'+{hour}'] = round(avg_row[0], 1) if avg_row[0] else None

    return glucose_levels


def predict_next_window(lookback_days=30, tz_name='UTC'):
    """
    Predict next glucose level and insulin dose using statistical baseline.

    Args:
        lookback_days: Number of days of historical data to use (default: 30)
        tz_name: IANA timezone name of the client (for next window label)

    Returns:
        dict: Prediction results with glucose, insulin, confidence, and warnings
    """
    # Calculate lookback start time in UTC
    now = datetime.now(timezone.utc)
    now_local = now.astimezone(ZoneInfo(tz_name))
    lookback_start = (now - timedelta(days=lookback_days)).strftime('%Y-%m-%d %H:%M:%S')

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Fetch historical glucose data in chronological order (ASC)
        # for time-weighted mean calculation
        cursor.execute('''
            SELECT timestamp, level
            FROM glucose
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (lookback_start,))
        glucose_data = cursor.fetchall()

        # Fetch historical insulin data in chronological order (ASC)
        cursor.execute('''
            SELECT timestamp, level
            FROM insulin
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (lookback_start,))
        insulin_data = cursor.fetchall()

        # Fetch recent intake data (last 7 days for calorie context)
        intake_start = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            SELECT i.timestamp, n.kcal * i.nutrition_amount / n.weight as calories
            FROM intake i
            JOIN nutrition n ON i.nutrition_id = n.id
            WHERE i.timestamp >= ?
            ORDER BY i.timestamp DESC
        ''', (intake_start,))
        intake_data = cursor.fetchall()

    # Data quality checks
    warnings = []
    if len(glucose_data) < 10:
        warnings.append("Insufficient data: Less than 10 glucose readings available")
        return {
            'next_window': _get_next_window_name(now_local),
            'prediction': None,
            'basis': {
                'data_points': len(glucose_data),
                'lookback_days': lookback_days
            },
            'warnings': warnings + ["Cannot generate prediction with insufficient data"],
            'error': 'insufficient_data'
        }

    # 1. Calculate predicted glucose using time-weighted mean of recent data
    # Use last 24 hours of data for prediction
    recent_cutoff = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    recent_glucose = [(row[0], row[1]) for row in glucose_data if row[0] >= recent_cutoff]

    if len(recent_glucose) < 2:
        # Fall back to last 2 readings if insufficient recent data
        # Data is in ASC order, so last 2 are the most recent
        recent_glucose = glucose_data[-2:] if len(glucose_data) >= 2 else glucose_data

    # Convert timestamp strings to datetime objects (data already in ASC order from SQL)
    recent_glucose_parsed = [
        (datetime.strptime(ts, '%Y-%m-%d %H:%M:%S'), level)
        for ts, level in recent_glucose
    ]
    predicted_glucose = calculate_time_weighted_mean(recent_glucose_parsed)

    # Check if time-weighted mean failed (can happen if all timestamps are identical)
    if predicted_glucose is None:
        # Use simple average of recent glucose values as fallback
        predicted_glucose = sum(row[1] for row in recent_glucose) / len(recent_glucose)
        warnings.append("Using simple average (insufficient time spread in data)")

    # Calculate glucose statistics for full dataset
    all_glucose_values = [row[1] for row in glucose_data]
    avg_glucose = sum(all_glucose_values) / len(all_glucose_values)
    glucose_std = math.sqrt(sum((x - avg_glucose) ** 2 for x in all_glucose_values) / len(all_glucose_values))

    # Calculate CV for confidence assessment
    cv = (glucose_std / avg_glucose * 100) if avg_glucose > 0 else 100

    # Calculate uncertainty range (±1 std dev)
    glucose_range = [
        max(40, predicted_glucose - glucose_std),
        min(500, predicted_glucose + glucose_std)
    ]

    # 2. Calculate insulin recommendation
    if len(insulin_data) > 0:
        # Calculate insulin-to-glucose ratio
        # Pair each insulin dose with nearest glucose reading
        insulin_glucose_pairs = []
        for insulin_ts, insulin_level in insulin_data:
            insulin_time = datetime.strptime(insulin_ts, '%Y-%m-%d %H:%M:%S')

            # Find closest glucose reading within 2 hours
            for glucose_ts, glucose_level in glucose_data:
                glucose_time = datetime.strptime(glucose_ts, '%Y-%m-%d %H:%M:%S')
                time_diff = abs((insulin_time - glucose_time).total_seconds())

                if time_diff <= 7200:  # 2 hours
                    insulin_glucose_pairs.append((insulin_level, glucose_level))
                    break

        if insulin_glucose_pairs:
            # Calculate average ratio
            ratios = [insulin / glucose for insulin, glucose in insulin_glucose_pairs if glucose > 0]
            avg_ratio = sum(ratios) / len(ratios) if ratios else 0

            # Apply ratio to predicted glucose
            recommended_insulin = predicted_glucose * avg_ratio

            # Adjust for recent calorie intake (last 24 hours)
            if len(intake_data) > 0:
                recent_calories = sum(row[1] for row in intake_data[:5] if row[1])  # Last 5 meals
                avg_calories = recent_calories / min(5, len(intake_data))

                # If calories are high (>100 kcal), slightly increase insulin (up to 10%)
                if avg_calories > 100:
                    calorie_factor = min(1.1, 1 + (avg_calories - 100) / 1000)
                    recommended_insulin *= calorie_factor

            # Apply safety bounds
            max_insulin = max([row[1] for row in insulin_data]) * 1.5 if insulin_data else 2.0
            recommended_insulin = max(0, min(recommended_insulin, max_insulin))

            avg_insulin = sum(row[1] for row in insulin_data) / len(insulin_data)
        else:
            # No valid insulin-glucose pairs found
            warnings.append("Unable to calculate insulin recommendation: No paired data")
            recommended_insulin = None
            avg_insulin = None
    else:
        warnings.append("No insulin data available for recommendation")
        recommended_insulin = None
        avg_insulin = None

    # 3. Assess confidence level
    confidence = _calculate_confidence(len(glucose_data), cv, glucose_std, all_glucose_values)

    # 4. Generate warnings
    if cv > 35:
        warnings.append("High glucose variability detected (CV > 35%)")

    if predicted_glucose < 60:
        warnings.append("⚠️ ALERT: Predicted hypoglycemia risk (< 60 mg/dL)")
    elif predicted_glucose > 400:
        warnings.append("⚠️ ALERT: Predicted hyperglycemia risk (> 400 mg/dL)")

    # Check for unusual patterns (>2 std dev from mean)
    if abs(predicted_glucose - avg_glucose) > 2 * glucose_std:
        warnings.append("Unusual pattern detected - prediction differs significantly from historical average")

    if not warnings:
        warnings.append("Monitor closely and adjust as needed")

    return {
        'next_window': _get_next_window_name(now_local),
        'prediction': {
            'glucose': round(predicted_glucose, 1),
            'glucose_range': [round(glucose_range[0], 1), round(glucose_range[1], 1)],
            'insulin_recommended': round(recommended_insulin, 2) if recommended_insulin else None,
            'confidence': confidence
        },
        'basis': {
            'data_points': len(glucose_data),
            'lookback_days': lookback_days,
            'recent_cv': round(cv, 1),
            'avg_glucose': round(avg_glucose, 1),
            'avg_insulin': round(avg_insulin, 2) if avg_insulin else None
        },
        'warnings': warnings
    }


def _get_next_window_name(current_time):
    """Determine the name of the next time window."""
    hour = current_time.hour

    # Day window: 05:00-16:59, Night window: 17:00-04:59
    if 5 <= hour < 17:
        # Currently in day window, next is night
        return "Night (17:00-04:59)"
    else:
        # Currently in night window, next is day
        return "Day (05:00-16:59)"


def _calculate_confidence(data_points, cv, std_dev, values):
    """Calculate confidence level for prediction."""
    # Check for stable recent trend (last 5 readings)
    if len(values) >= 5:
        recent_values = values[:5]
        recent_std = math.sqrt(sum((x - sum(recent_values)/len(recent_values)) ** 2 for x in recent_values) / len(recent_values))
        stable_trend = recent_std < std_dev * 0.8
    else:
        stable_trend = False

    # Confidence criteria
    if cv < 25 and data_points >= 30 and stable_trend:
        return "High"
    elif cv < 35 and data_points >= 14:
        return "Medium"
    else:
        return "Low"


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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT kcal_per_gram FROM nutrition WHERE id = ?', (nutrition_id,))
            kcal_per_gram = cursor.fetchone()

            if not kcal_per_gram:
                raise ValueError('Nutrition not found')

            nutrition_kcal = nutrition_amount * kcal_per_gram[0]
            cursor.execute('''INSERT INTO intake
                            (nutrition_id, timestamp, nutrition_amount, nutrition_kcal)
                            VALUES (?, ?, ?, ?)''',
                         (nutrition_id, timestamp, nutrition_amount, nutrition_kcal))
            conn.commit()
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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT kcal_per_gram FROM nutrition WHERE id = ?', (nutrition_id,))
            kcal_per_gram = cursor.fetchone()

            if not kcal_per_gram:
                raise ValueError('Nutrition not found')

            nutrition_kcal = nutrition_amount * kcal_per_gram[0]
            cursor.execute('''UPDATE intake
                            SET timestamp = ?, nutrition_id = ?, nutrition_amount = ?, nutrition_kcal = ?
                            WHERE id = ?''',
                         (timestamp, nutrition_id, nutrition_amount, nutrition_kcal, record_id))
            conn.commit()

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
    def get_list_with_filter(query, start_date, end_date, tz_name='UTC', default_hours=24):
        if start_date and end_date:
            utc_start, _ = to_utc_range(start_date, tz_name)
            _, utc_end = to_utc_range(end_date, tz_name)
            rows = execute_query(query, (utc_start, utc_end))
        else:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=default_hours)).strftime('%Y-%m-%d %H:%M:%S')
            query = query.replace('BETWEEN ? AND ?', '>= ?')
            rows = execute_query(query, (cutoff,))
        return rows


# ============================================================================
# HTTP Request Handler
# ============================================================================

class GlucoseHandler(http.server.SimpleHTTPRequestHandler):

    # Close idle/slow connections after this many seconds (Slowloris mitigation)
    timeout = REQUEST_TIMEOUT

    def guess_type(self, path):
        """Override to properly handle .dev extension as HTML."""
        if path.endswith('.html.dev'):
            return 'text/html'
        return super().guess_type(path)

    def list_directory(self, path):
        """Redirect root directory to index.html (or index.html.dev when DEBUG_STATIC)."""
        index_file = 'index.html.dev' if DEBUG_STATIC else 'index.html'
        self.send_response(301)
        self.send_header('Location', f'/static/{index_file}')
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
        """Route HTTP request logs through the standard logger."""
        logger.info(format % args)

    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            query_params = urllib.parse.parse_qs(parsed_path.query)

            # When DEBUG_STATIC, redirect index.html to index.html.dev
            if DEBUG_STATIC and path == '/static/index.html':
                self.send_response(301)
                self.send_header('Location', '/static/index.html.dev')
                self.end_headers()
                return

            route_handlers = {
                '/api/nutrition': lambda: self._send_json(DataAccess.get_nutrition_list()),
                '/api/supplements': lambda: self._send_json(DataAccess.get_supplements_list()),
                '/api/intake/previous-window': lambda: self.handle_get_previous_window_intake(query_params),
                '/api/glucose': lambda: self.handle_get_list('glucose', query_params),
                '/api/insulin': lambda: self.handle_get_list('insulin', query_params),
                '/api/intake': lambda: self.handle_get_intake_list(query_params),
                '/api/supplement-intake': lambda: self.handle_get_supplement_intake_list(query_params),
                '/api/event': lambda: self.handle_get_event_list(query_params),
                '/api/dashboard/glucose-chart': lambda: self.handle_get_glucose_chart(query_params),
                '/api/dashboard/summary': lambda: self.handle_get_summary(query_params),
                '/api/dashboard/cv-charts': lambda: self.handle_get_cv_charts(query_params),
                '/api/dashboard/risk-metrics': lambda: self.handle_get_risk_metrics(query_params),
                '/api/dashboard/prediction': lambda: self.handle_get_prediction(query_params),
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
            if content_length > MAX_BODY_BYTES:
                self._send_error_json(f'Request body too large (max {MAX_BODY_BYTES} bytes)', 413)
                return
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
            if content_length > MAX_BODY_BYTES:
                self._send_error_json(f'Request body too large (max {MAX_BODY_BYTES} bytes)', 413)
                return
            raw_body = self.rfile.read(content_length)
            data = json.loads(raw_body.decode('utf-8'))
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
        tz_name = parse_tz(query_params, required=False)
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]

        query = f'''SELECT id, timestamp, level FROM {table}
                   WHERE timestamp BETWEEN ? AND ?
                   ORDER BY timestamp DESC'''

        rows = DataAccess.get_list_with_filter(query, start_date, end_date, tz_name)
        records = [{'id': row[0], 'timestamp': row[1], 'level': row[2]} for row in rows]
        self._send_json(records)

    def handle_get_intake_list(self, query_params):
        tz_name = parse_tz(query_params, required=False)
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]

        query = '''SELECT i.id, i.timestamp, i.nutrition_id, n.nutrition_name,
                         i.nutrition_amount, i.nutrition_kcal
                  FROM intake i
                  JOIN nutrition n ON i.nutrition_id = n.id
                  WHERE i.timestamp BETWEEN ? AND ?
                  ORDER BY i.timestamp DESC'''

        rows = DataAccess.get_list_with_filter(query, start_date, end_date, tz_name)
        records = [{'id': row[0], 'timestamp': row[1], 'nutrition_id': row[2],
                   'nutrition_name': row[3], 'nutrition_amount': row[4],
                   'nutrition_kcal': row[5]} for row in rows]
        self._send_json(records)

    def handle_get_supplement_intake_list(self, query_params):
        tz_name = parse_tz(query_params, required=False)
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]

        query = '''SELECT si.id, si.timestamp, si.supplement_id, s.supplement_name,
                         si.supplement_amount
                  FROM supplement_intake si
                  JOIN supplements s ON si.supplement_id = s.id
                  WHERE si.timestamp BETWEEN ? AND ?
                  ORDER BY si.timestamp DESC'''

        rows = DataAccess.get_list_with_filter(query, start_date, end_date, tz_name)
        records = [{'id': row[0], 'timestamp': row[1], 'supplement_id': row[2],
                   'supplement_name': row[3], 'supplement_amount': row[4]} for row in rows]
        self._send_json(records)

    def handle_get_event_list(self, query_params):
        tz_name = parse_tz(query_params, required=False)
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]

        query = '''SELECT id, timestamp, event_name, event_notes
                  FROM event
                  WHERE timestamp BETWEEN ? AND ?
                  ORDER BY timestamp DESC'''

        rows = DataAccess.get_list_with_filter(query, start_date, end_date, tz_name)
        records = [{'id': row[0], 'timestamp': row[1], 'event_name': row[2],
                   'event_notes': row[3]} for row in rows]
        self._send_json(records)

    def handle_get_previous_window_intake(self, query_params):
        try:
            tz_name = parse_tz(query_params, required=True)
        except ValueError as e:
            self._send_error_json(str(e), 400)
            return
        prev_start, prev_end = get_previous_time_window(tz_name)

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
        tz_name = parse_tz(query_params, required=False)
        today = today_in_tz(tz_name)
        start_date = query_params.get('start_date', [f'{today.year}-01-01'])[0]
        end_date = query_params.get('end_date', [f'{today.year}-12-31'])[0]

        utc_start, _ = to_utc_range(start_date, tz_name)
        _, utc_end = to_utc_range(end_date, tz_name)

        glucose_query = '''SELECT timestamp, level FROM glucose
                          WHERE timestamp BETWEEN ? AND ?
                          ORDER BY timestamp'''

        insulin_query = '''SELECT timestamp, level FROM insulin
                          WHERE timestamp BETWEEN ? AND ?
                          ORDER BY timestamp'''

        glucose_rows = execute_query(glucose_query, (utc_start, utc_end))
        insulin_rows = execute_query(insulin_query, (utc_start, utc_end))

        weekly_data = calculate_weekly_mean_both(glucose_rows, insulin_rows)
        self._send_json(weekly_data)

    def handle_get_summary(self, query_params):
        try:
            tz_name = parse_tz(query_params, required=True)
        except ValueError as e:
            self._send_error_json(str(e), 400)
            return

        today = today_in_tz(tz_name)
        start_date = query_params.get('start_date', [f'{today.year}-{today.month:02d}-01'])[0]

        # Calculate last day of current month in client timezone
        if today.month == 12:
            default_end = f'{today.year}-12-31'
        else:
            next_month = date(today.year, today.month + 1, 1)
            default_end = str(date(next_month.year, next_month.month, 1) - timedelta(days=1))

        end_date = query_params.get('end_date', [default_end])[0]

        with get_db_connection() as conn:
            cursor = conn.cursor()

            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            summary_data = []
            current_dt = start_dt

            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                current_date = current_dt.date()

                # Day window: 05:00-16:59 local → UTC
                day_start_utc = local_5am_utc(current_date, tz_name)
                day_end_utc = day_start_utc + timedelta(hours=12)
                day_data = process_time_window_summary(cursor, '☀️', date_str,
                                                      day_start_utc.strftime('%Y-%m-%d %H:%M:%S'),
                                                      day_end_utc.strftime('%Y-%m-%d %H:%M:%S'))
                if day_data:
                    summary_data.append(day_data)

                # Night window: 17:00 local to 05:00 next day local → UTC
                next_date = (current_dt + timedelta(days=1)).date()
                night_end_utc = local_5am_utc(next_date, tz_name)
                night_data = process_time_window_summary(cursor, '🌙', date_str,
                                                        day_end_utc.strftime('%Y-%m-%d %H:%M:%S'),
                                                        night_end_utc.strftime('%Y-%m-%d %H:%M:%S'))
                if night_data:
                    summary_data.append(night_data)

                current_dt += timedelta(days=1)

        self._send_json(summary_data)

    def handle_get_cv_charts(self, query_params):
        try:
            tz_name = parse_tz(query_params, required=True)
        except ValueError as e:
            self._send_error_json(str(e), 400)
            return

        today = today_in_tz(tz_name)
        end_date_str = query_params.get('end_date', [today.strftime('%Y-%m-%d')])[0]
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        start_30_days = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
        utc_start, _ = to_utc_range(start_30_days, tz_name)
        _, utc_end = to_utc_range(end_date_str, tz_name)

        glucose_query = '''SELECT timestamp, level FROM glucose
                          WHERE timestamp BETWEEN ? AND ?
                          ORDER BY timestamp'''
        glucose_rows = execute_query(glucose_query, (utc_start, utc_end))

        windows_7d_12h = generate_cv_windows(end_date, 7, 12, tz_name)
        windows_30d_48h = generate_cv_windows(end_date, 30, 48, tz_name)
        windows_30d_5d = generate_cv_windows(end_date, 30, 120, tz_name)

        self._send_json({
            'cv_7d_12h': calculate_cv_data(glucose_rows, windows_7d_12h),
            'cv_30d_48h': calculate_cv_data(glucose_rows, windows_30d_48h),
            'cv_30d_5d': calculate_cv_data(glucose_rows, windows_30d_5d)
        })

    def handle_get_risk_metrics(self, query_params):
        try:
            tz_name = parse_tz(query_params, required=True)
        except ValueError as e:
            self._send_error_json(str(e), 400)
            return

        today = today_in_tz(tz_name)
        end_date_str = query_params.get('end_date', [today.strftime('%Y-%m-%d')])[0]
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        start_30_days = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
        utc_start, _ = to_utc_range(start_30_days, tz_name)
        _, utc_end = to_utc_range(end_date_str, tz_name)

        glucose_query = '''SELECT timestamp, level FROM glucose
                          WHERE timestamp BETWEEN ? AND ?
                          ORDER BY timestamp'''
        glucose_rows = execute_query(glucose_query, (utc_start, utc_end))

        windows_7d_12h = generate_cv_windows(end_date, 7, 12, tz_name)
        windows_30d_48h = generate_cv_windows(end_date, 30, 48, tz_name)
        windows_30d_5d = generate_cv_windows(end_date, 30, 120, tz_name)

        self._send_json({
            'lbgi_7d_12h': calculate_risk_metric_data(glucose_rows, windows_7d_12h, 'lbgi'),
            'lbgi_30d_48h': calculate_risk_metric_data(glucose_rows, windows_30d_48h, 'lbgi'),
            'lbgi_30d_5d': calculate_risk_metric_data(glucose_rows, windows_30d_5d, 'lbgi'),
            'hbgi_7d_12h': calculate_risk_metric_data(glucose_rows, windows_7d_12h, 'hbgi'),
            'hbgi_30d_48h': calculate_risk_metric_data(glucose_rows, windows_30d_48h, 'hbgi'),
            'hbgi_30d_5d': calculate_risk_metric_data(glucose_rows, windows_30d_5d, 'hbgi'),
            'adrr_7d_12h': calculate_adrr_data(glucose_rows, windows_7d_12h),
            'adrr_30d_48h': calculate_adrr_data(glucose_rows, windows_30d_48h),
            'adrr_30d_5d': calculate_adrr_data(glucose_rows, windows_30d_5d)
        })

    def handle_get_prediction(self, query_params):
        """Handle GET /api/dashboard/prediction - Get glucose and insulin prediction."""
        try:
            tz_name = parse_tz(query_params, required=True)
        except ValueError as e:
            self._send_error_json(str(e), 400)
            return

        lookback_days = int(query_params.get('lookback_days', [30])[0])

        try:
            result = predict_next_window(lookback_days, tz_name)
            self._send_json(result)
        except Exception as e:
            logger.exception("Prediction error: %s", e)
            self._send_json({
                'error': 'prediction_failed',
                'message': str(e),
                'warnings': ['Unable to generate prediction due to error']
            }, status=500)


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
            date_str = result.stdout.strip().split('=')[1]
            exp_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
            days_left = (exp_date - datetime.now()).days

            if days_left < 0:
                logger.error("Certificate %s has EXPIRED!", cert_path)
            elif days_left < 30:
                logger.warning("Certificate %s expires in %d days!", cert_path, days_left)
    except Exception as e:
        logger.warning("Could not check certificate expiration: %s", e)


def create_ssl_context():
    """Create and configure SSL context for mTLS."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Require client certificates
    context.verify_mode = ssl.CERT_REQUIRED

    # Load CA certificate for client verification
    context.load_verify_locations(cafile=CA_CERT_PATH)

    # Load server certificate and key
    context.load_cert_chain(certfile=SERVER_CERT_PATH, keyfile=SERVER_KEY_PATH)

    # Require TLS 1.3 minimum. TLS 1.3 cipher suites are fixed by the
    # protocol, so set_ciphers() is not needed.
    context.minimum_version = ssl.TLSVersion.TLSv1_3

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
            logger.info("Client connected: %s from %s", cn, client_address[0])
    except Exception as e:
        logger.warning("Could not retrieve client certificate: %s", e)


class GlucoseServer(socketserver.ThreadingTCPServer):
    """ThreadingTCPServer with a bounded worker pool and error logging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def process_request(self, request, client_address):
        """Submit each request to the bounded pool instead of spawning unbounded threads."""
        self._executor.submit(self.process_request_thread, request, client_address)

    def server_close(self):
        self._executor.shutdown(wait=False)
        super().server_close()

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if getattr(exc, 'skip_traceback', False):
            logger.warning("Error from %s: %s", client_address[0], exc)
        else:
            logger.exception("Unhandled exception processing request from %s", client_address[0])


class SecureGlucoseHandler(GlucoseHandler):
    """Extended handler that logs client certificate info."""

    def setup(self):
        # super().setup() applies REQUEST_TIMEOUT to the socket, so the
        # handshake is bounded by that timeout.
        super().setup()
        try:
            self.request.do_handshake()
        except (ssl.SSLError, OSError) as e:
            logger.warning("TLS handshake failed from %s: %s", self.client_address[0], e)
            e.skip_traceback = True
            raise
        log_client_certificate(self.request, self.client_address)


def main():
    if not os.path.exists(DB_PATH):
        logger.error("Database %s not found. Please run init_db.py first.", DB_PATH)
        return

    global _db_pool
    _db_pool = ConnectionPool(DB_PATH, size=DB_POOL_SIZE)

    # Set WAL mode once at startup (it persists in the DB file)
    with get_db_connection() as conn:
        conn.execute('PRAGMA journal_mode=WAL')

    GlucoseServer.allow_reuse_address = True
    GlucoseServer.daemon_threads = True

    if MTLS_ENABLED:
        # Check if certificate files exist
        if not all(os.path.exists(p) for p in [CA_CERT_PATH, SERVER_CERT_PATH, SERVER_KEY_PATH]):
            logger.error("mTLS is enabled but certificate files not found!")
            logger.error("Run ./generate-certs.sh to generate certificates, "
                         "or set MTLS_ENABLED=false to disable mTLS.")
            return

        # Create HTTPS server with mTLS (multi-threaded)
        with GlucoseServer(("", PORT), SecureGlucoseHandler) as httpd:
            ssl_context = create_ssl_context()
            # do_handshake_on_connect=False defers the TLS handshake out of
            # accept() on the main thread.  The handshake is performed in
            # SecureGlucoseHandler.setup() on a worker thread, where the
            # REQUEST_TIMEOUT socket timeout is already in effect.
            httpd.socket = ssl_context.wrap_socket(
                httpd.socket, server_side=True, do_handshake_on_connect=False
            )

            logger.info("mTLS enabled - Server running at https://localhost:%d/", PORT)
            logger.info("Clients must present valid certificates signed by the CA")
            logger.info("Static: %s",
                        'index.html.dev (DEBUG_STATIC)' if DEBUG_STATIC else 'index.html')
            httpd.serve_forever()
    else:
        # Run without mTLS (development mode, multi-threaded)
        logger.warning("mTLS is DISABLED - running in insecure mode!")
        logger.info("Server running at http://localhost:%d/", PORT)
        logger.info("Static: %s",
                    'index.html.dev (DEBUG_STATIC)' if DEBUG_STATIC else 'index.html')

        with GlucoseServer(("", PORT), GlucoseHandler) as httpd:
            httpd.serve_forever()


if __name__ == '__main__':
    main()
