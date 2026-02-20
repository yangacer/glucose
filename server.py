#!/usr/bin/env python3

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
from datetime import datetime, date, timedelta
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

def get_db_connection():
    """Create and return a database connection."""
    return sqlite3.connect(DB_PATH)


def execute_query(query, params=(), fetch_one=False, commit=False):
    """Execute a query and return results or commit changes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    if commit:
        conn.commit()
        result = True
    elif fetch_one:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()
    
    conn.close()
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


def get_previous_time_window():
    """Calculate previous 12-hour time window."""
    now = datetime.now()
    current_hour = now.hour
    
    if current_hour < 12:  # Current is AM, previous is yesterday PM
        prev_start = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 12:00:00'
        prev_end = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 23:59:59'
    else:  # Current is PM, previous is today AM
        prev_start = now.strftime('%Y-%m-%d') + ' 00:00:00'
        prev_end = now.strftime('%Y-%m-%d') + ' 11:59:59'
    
    return prev_start, prev_end


def process_time_window_summary(cursor, am_pm, date_str, window_start, window_end):
    """Process and aggregate data for a 12-hour time window."""
    # Get all intakes in this window
    cursor.execute('''SELECT i.timestamp, i.nutrition_kcal, i.nutrition_amount, n.nutrition_name
                     FROM intake i
                     JOIN nutrition n ON i.nutrition_id = n.id
                     WHERE i.timestamp BETWEEN ? AND ?
                     ORDER BY i.timestamp''',
                  (window_start, window_end))
    intakes = cursor.fetchall()
    
    if not intakes:
        return None
    
    # Use first intake time as reference
    first_intake_time = intakes[0][0]
    intake_dt = datetime.strptime(first_intake_time, '%Y-%m-%d %H:%M:%S')
    
    # Aggregate nutrition data
    total_kcal = sum(row[1] for row in intakes)
    nutrition_items = [f"{row[3]} ({row[1]:.1f} kcal)" for row in intakes]
    nutrition_str = ', '.join(nutrition_items)
    
    # Get insulin dose in this window
    cursor.execute('''SELECT timestamp, level FROM insulin
                     WHERE timestamp BETWEEN ? AND ?
                     ORDER BY timestamp DESC LIMIT 1''',
                  (window_start, window_end))
    insulin_row = cursor.fetchone()
    dose_time = insulin_row[0] if insulin_row else None
    dosage = insulin_row[1] if insulin_row else None
    
    # Get glucose levels before and after intake
    glucose_levels = get_glucose_levels_around_intake(cursor, first_intake_time, intake_dt)
    
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
    
    return {
        'am_pm': am_pm,
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
    """Get glucose levels before and hourly after intake."""
    glucose_levels = {}
    
    # Before intake
    cursor.execute('''SELECT level FROM glucose
                     WHERE timestamp <= ?
                     ORDER BY timestamp DESC LIMIT 1''',
                  (first_intake_time,))
    before_row = cursor.fetchone()
    glucose_levels['before'] = before_row[0] if before_row else None
    
    # After intake (+1hr to +12hr)
    for hour in range(1, 13):
        target_time = intake_dt + timedelta(hours=hour)
        
        # Get average glucose in ±30min window
        window_start_time = (target_time - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        window_end_time = (target_time + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''SELECT AVG(level) FROM glucose
                         WHERE timestamp BETWEEN ? AND ?''',
                      (window_start_time, window_end_time))
        avg_row = cursor.fetchone()
        glucose_levels[f'+{hour}hr'] = round(avg_row[0], 1) if avg_row[0] else None
    
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
    
    def do_GET(self):
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
        }
        
        if path in route_handlers:
            route_handlers[path]()
        else:
            super().do_GET()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
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
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
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
        conn = get_db_connection()
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
        
        conn.close()
        
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
        
        query = '''SELECT timestamp, level FROM glucose 
                  WHERE timestamp BETWEEN ? AND ? 
                  ORDER BY timestamp'''
        
        rows = execute_query(query, (start_date, end_date + ' 23:59:59'))
        weekly_data = calculate_weekly_mean(rows)
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all dates in range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        summary_data = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y-%m-%d')
            
            # Process AM window (00:00-12:00)
            am_window_start = f'{date_str} 00:00:00'
            am_window_end = f'{date_str} 11:59:59'
            am_data = process_time_window_summary(cursor, 'AM', date_str, 
                                                 am_window_start, am_window_end)
            if am_data:
                summary_data.append(am_data)
            
            # Process PM window (12:00-24:00)
            pm_window_start = f'{date_str} 12:00:00'
            pm_window_end = f'{date_str} 23:59:59'
            pm_data = process_time_window_summary(cursor, 'PM', date_str, 
                                                 pm_window_start, pm_window_end)
            if pm_data:
                summary_data.append(pm_data)
            
            current_dt += timedelta(days=1)
        
        conn.close()
        self._send_json(summary_data)


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
    
    if MTLS_ENABLED:
        # Check if certificate files exist
        if not all(os.path.exists(p) for p in [CA_CERT_PATH, SERVER_CERT_PATH, SERVER_KEY_PATH]):
            print("ERROR: mTLS is enabled but certificate files not found!")
            print("Please run ./generate-certs.sh to generate certificates.")
            print("Or set MTLS_ENABLED=false to disable mTLS.")
            return
        
        # Create HTTPS server with mTLS
        with socketserver.TCPServer(("", PORT), SecureGlucoseHandler) as httpd:
            ssl_context = create_ssl_context()
            httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
            
            print(f"✓ mTLS enabled - Server running at https://localhost:{PORT}/")
            print(f"  Clients must present valid certificates signed by the CA")
            print(f"  See CLIENT.md for client configuration instructions")
            httpd.serve_forever()
    else:
        # Run without mTLS (development mode)
        print("WARNING: mTLS is DISABLED - running in insecure mode!")
        print(f"Server running at http://localhost:{PORT}/")
        
        with socketserver.TCPServer(("", PORT), GlucoseHandler) as httpd:
            httpd.serve_forever()


if __name__ == '__main__':
    main()
