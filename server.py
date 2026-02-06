#!/usr/bin/env python3

import http.server
import socketserver
import json
import sqlite3
import urllib.parse
from datetime import datetime, date, timedelta
import os

PORT = 8000
DB_PATH = 'glucose.db'

class GlucoseHandler(http.server.SimpleHTTPRequestHandler):
    
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if path == '/api/nutrition':
            self.handle_get_nutrition()
        elif path == '/api/intake/previous-window':
            self.handle_get_previous_window_intake()
        elif path == '/api/glucose':
            self.handle_get_glucose_list(query_params)
        elif path == '/api/insulin':
            self.handle_get_insulin_list(query_params)
        elif path == '/api/intake':
            self.handle_get_intake_list(query_params)
        elif path == '/api/supplements':
            self.handle_get_supplements_list(query_params)
        elif path == '/api/event':
            self.handle_get_event_list(query_params)
        elif path == '/api/dashboard/glucose-chart':
            start_date = query_params.get('start_date', [f'{date.today().year}-01-01'])[0]
            end_date = query_params.get('end_date', [f'{date.today().year}-12-31'])[0]
            self.handle_get_glucose_chart(start_date, end_date)
        elif path == '/api/dashboard/summary':
            today = date.today()
            start_date = query_params.get('start_date', [f'{today.year}-{today.month:02d}-01'])[0]
            # Calculate last day of current month
            if today.month == 12:
                end_date = f'{today.year}-12-31'
            else:
                next_month = date(today.year, today.month + 1, 1)
                end_date = str(date(next_month.year, next_month.month, 1) - timedelta(days=1))
            end_date = query_params.get('end_date', [end_date])[0]
            self.handle_get_summary(start_date, end_date)
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        if self.path == '/api/glucose':
            self.handle_post_glucose(data)
        elif self.path == '/api/insulin':
            self.handle_post_insulin(data)
        elif self.path == '/api/intake':
            self.handle_post_intake(data)
        elif self.path == '/api/supplements':
            self.handle_post_supplements(data)
        elif self.path == '/api/event':
            self.handle_post_event(data)
        elif self.path == '/api/nutrition':
            self.handle_post_nutrition(data)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def do_PUT(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        if self.path.startswith('/api/glucose/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_update_glucose(record_id, data)
        elif self.path.startswith('/api/insulin/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_update_insulin(record_id, data)
        elif self.path.startswith('/api/intake/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_update_intake(record_id, data)
        elif self.path.startswith('/api/supplements/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_update_supplements(record_id, data)
        elif self.path.startswith('/api/event/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_update_event(record_id, data)
        elif self.path.startswith('/api/nutrition/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_update_nutrition(record_id, data)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def do_DELETE(self):
        if self.path.startswith('/api/glucose/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_delete_glucose(record_id)
        elif self.path.startswith('/api/insulin/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_delete_insulin(record_id)
        elif self.path.startswith('/api/intake/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_delete_intake(record_id)
        elif self.path.startswith('/api/supplements/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_delete_supplements(record_id)
        elif self.path.startswith('/api/event/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_delete_event(record_id)
        elif self.path.startswith('/api/nutrition/'):
            record_id = int(self.path.split('/')[-1])
            self.handle_delete_nutrition(record_id)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def handle_post_glucose(self, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO glucose (timestamp, level) VALUES (?, ?)',
                      (data['timestamp'], data['level']))
        conn.commit()
        conn.close()
        self._set_headers(201)
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_post_insulin(self, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO insulin (timestamp, level) VALUES (?, ?)',
                      (data['timestamp'], data['level']))
        conn.commit()
        conn.close()
        self._set_headers(201)
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_post_intake(self, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Get kcal_per_gram from nutrition table
        cursor.execute('SELECT kcal_per_gram FROM nutrition WHERE id = ?',
                      (data['nutrition_id'],))
        result = cursor.fetchone()
        if not result:
            conn.close()
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': 'Nutrition not found'}).encode())
            return
        
        kcal_per_gram = result[0]
        nutrition_kcal = data['nutrition_amount'] * kcal_per_gram
        
        cursor.execute('''INSERT INTO intake 
                         (nutrition_id, timestamp, nutrition_amount, nutrition_kcal) 
                         VALUES (?, ?, ?, ?)''',
                      (data['nutrition_id'], data['timestamp'], 
                       data['nutrition_amount'], nutrition_kcal))
        conn.commit()
        conn.close()
        self._set_headers(201)
        self.wfile.write(json.dumps({'success': True, 'nutrition_kcal': nutrition_kcal}).encode())
    
    def handle_post_supplements(self, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO supplements 
                         (timestamp, supplement_name, supplement_amount) 
                         VALUES (?, ?, ?)''',
                      (data['timestamp'], data['supplement_name'], 
                       data['supplement_amount']))
        conn.commit()
        conn.close()
        self._set_headers(201)
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_post_event(self, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO event 
                         (timestamp, event_name, event_notes) 
                         VALUES (?, ?, ?)''',
                      (data['timestamp'], data['event_name'], 
                       data.get('event_notes', '')))
        conn.commit()
        conn.close()
        self._set_headers(201)
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_post_nutrition(self, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO nutrition 
                         (nutrition_name, kcal, weight) 
                         VALUES (?, ?, ?)''',
                      (data['nutrition_name'], data['kcal'], data['weight']))
        conn.commit()
        conn.close()
        self._set_headers(201)
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_get_nutrition(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, nutrition_name, kcal, weight, kcal_per_gram FROM nutrition')
        rows = cursor.fetchall()
        conn.close()
        
        nutrition_list = [{'id': row[0], 'nutrition_name': row[1], 
                          'kcal': row[2], 'weight': row[3], 'kcal_per_gram': row[4]} for row in rows]
        
        self._set_headers()
        self.wfile.write(json.dumps(nutrition_list).encode())
    
    def handle_get_glucose_list(self, query_params):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get filter parameters
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        if start_date and end_date:
            cursor.execute('''SELECT id, timestamp, level FROM glucose 
                             WHERE timestamp BETWEEN ? AND ? 
                             ORDER BY timestamp DESC''',
                          (start_date, end_date + ' 23:59:59'))
        else:
            # Default: last 24 hours
            cursor.execute('''SELECT id, timestamp, level FROM glucose 
                             WHERE timestamp >= datetime('now', '-1 day')
                             ORDER BY timestamp DESC''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = [{'id': row[0], 'timestamp': row[1], 'level': row[2]} for row in rows]
        self._set_headers()
        self.wfile.write(json.dumps(records).encode())
    
    def handle_get_insulin_list(self, query_params):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        if start_date and end_date:
            cursor.execute('''SELECT id, timestamp, level FROM insulin 
                             WHERE timestamp BETWEEN ? AND ? 
                             ORDER BY timestamp DESC''',
                          (start_date, end_date + ' 23:59:59'))
        else:
            cursor.execute('''SELECT id, timestamp, level FROM insulin 
                             WHERE timestamp >= datetime('now', '-1 day')
                             ORDER BY timestamp DESC''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = [{'id': row[0], 'timestamp': row[1], 'level': row[2]} for row in rows]
        self._set_headers()
        self.wfile.write(json.dumps(records).encode())
    
    def handle_get_intake_list(self, query_params):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        if start_date and end_date:
            cursor.execute('''SELECT i.id, i.timestamp, i.nutrition_id, n.nutrition_name, 
                                    i.nutrition_amount, i.nutrition_kcal
                             FROM intake i
                             JOIN nutrition n ON i.nutrition_id = n.id
                             WHERE i.timestamp BETWEEN ? AND ? 
                             ORDER BY i.timestamp DESC''',
                          (start_date, end_date + ' 23:59:59'))
        else:
            cursor.execute('''SELECT i.id, i.timestamp, i.nutrition_id, n.nutrition_name, 
                                    i.nutrition_amount, i.nutrition_kcal
                             FROM intake i
                             JOIN nutrition n ON i.nutrition_id = n.id
                             WHERE i.timestamp >= datetime('now', '-1 day')
                             ORDER BY i.timestamp DESC''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = [{'id': row[0], 'timestamp': row[1], 'nutrition_id': row[2], 
                   'nutrition_name': row[3], 'nutrition_amount': row[4], 
                   'nutrition_kcal': row[5]} for row in rows]
        self._set_headers()
        self.wfile.write(json.dumps(records).encode())
    
    def handle_get_supplements_list(self, query_params):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        if start_date and end_date:
            cursor.execute('''SELECT id, timestamp, supplement_name, supplement_amount 
                             FROM supplements 
                             WHERE timestamp BETWEEN ? AND ? 
                             ORDER BY timestamp DESC''',
                          (start_date, end_date + ' 23:59:59'))
        else:
            cursor.execute('''SELECT id, timestamp, supplement_name, supplement_amount 
                             FROM supplements 
                             WHERE timestamp >= datetime('now', '-1 day')
                             ORDER BY timestamp DESC''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = [{'id': row[0], 'timestamp': row[1], 'supplement_name': row[2], 
                   'supplement_amount': row[3]} for row in rows]
        self._set_headers()
        self.wfile.write(json.dumps(records).encode())
    
    def handle_get_event_list(self, query_params):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        start_date = query_params.get('start_date', [None])[0]
        end_date = query_params.get('end_date', [None])[0]
        
        if start_date and end_date:
            cursor.execute('''SELECT id, timestamp, event_name, event_notes 
                             FROM event 
                             WHERE timestamp BETWEEN ? AND ? 
                             ORDER BY timestamp DESC''',
                          (start_date, end_date + ' 23:59:59'))
        else:
            cursor.execute('''SELECT id, timestamp, event_name, event_notes 
                             FROM event 
                             WHERE timestamp >= datetime('now', '-1 day')
                             ORDER BY timestamp DESC''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = [{'id': row[0], 'timestamp': row[1], 'event_name': row[2], 
                   'event_notes': row[3]} for row in rows]
        self._set_headers()
        self.wfile.write(json.dumps(records).encode())
    
    def handle_get_previous_window_intake(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current time and determine windows
        now = datetime.now()
        current_hour = now.hour
        
        # Determine previous window
        if current_hour < 12:  # Current is AM, previous is yesterday PM
            prev_start = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 12:00:00'
            prev_end = (now - timedelta(days=1)).strftime('%Y-%m-%d') + ' 23:59:59'
        else:  # Current is PM, previous is today AM
            prev_start = now.strftime('%Y-%m-%d') + ' 00:00:00'
            prev_end = now.strftime('%Y-%m-%d') + ' 11:59:59'
        
        # Get intake records from previous window
        cursor.execute('''SELECT i.nutrition_id, n.nutrition_name, i.nutrition_amount
                         FROM intake i
                         JOIN nutrition n ON i.nutrition_id = n.id
                         WHERE i.timestamp BETWEEN ? AND ?
                         ORDER BY i.timestamp ASC''',
                      (prev_start, prev_end))
        rows = cursor.fetchall()
        conn.close()
        
        records = [{'nutrition_id': row[0], 'nutrition_name': row[1], 
                   'nutrition_amount': row[2]} for row in rows]
        self._set_headers()
        self.wfile.write(json.dumps(records).encode())
    
    def handle_get_glucose_chart(self, start_date, end_date):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get glucose data within date range
        cursor.execute('''SELECT timestamp, level FROM glucose 
                         WHERE timestamp BETWEEN ? AND ? 
                         ORDER BY timestamp''',
                      (start_date, end_date + ' 23:59:59'))
        rows = cursor.fetchall()
        conn.close()
        
        # Calculate time-weighted mean by week
        weekly_data = self._calculate_weekly_mean(rows)
        
        self._set_headers()
        self.wfile.write(json.dumps(weekly_data).encode())
    
    def _calculate_weekly_mean(self, rows):
        if len(rows) < 2:
            return []
        
        from collections import defaultdict
        weekly_data = defaultdict(list)
        
        for timestamp_str, level in rows:
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            iso_year, iso_week, _ = dt.isocalendar()
            week_key = f'{iso_year}/W{iso_week:02d}'
            weekly_data[week_key].append((dt, level))
        
        result = []
        for week_key in sorted(weekly_data.keys()):
            data = weekly_data[week_key]
            mean = self._time_weighted_mean(data)
            if mean is not None:
                result.append({'week': week_key, 'mean': round(mean, 2)})
        
        return result
    
    def _time_weighted_mean(self, data):
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
        
        if total_time == 0:
            return None
        return total_area / total_time
    
    def handle_get_summary(self, start_date, end_date):
        conn = sqlite3.connect(DB_PATH)
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
            summary_data.append(self._process_time_window(cursor, 'AM', date_str, am_window_start, am_window_end))
            
            # Process PM window (12:00-24:00)
            pm_window_start = f'{date_str} 12:00:00'
            pm_window_end = f'{date_str} 23:59:59'
            summary_data.append(self._process_time_window(cursor, 'PM', date_str, pm_window_start, pm_window_end))
            
            current_dt += timedelta(days=1)
        
        conn.close()
        
        self._set_headers()
        self.wfile.write(json.dumps(summary_data).encode())
    
    def _process_time_window(self, cursor, am_pm, date_str, window_start, window_end):
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
        
        # Get glucose levels before and after intake (hourly for 12 hours)
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
        
        # Get events in window
        cursor.execute('''SELECT event_name FROM event
                         WHERE timestamp BETWEEN ? AND ?
                         ORDER BY timestamp''',
                      (window_start, window_end))
        events = cursor.fetchall()
        grouped_events = ', '.join([e[0] for e in events]) if events else ''
        
        # Get supplements in window
        cursor.execute('''SELECT supplement_name, supplement_amount FROM supplements
                         WHERE timestamp BETWEEN ? AND ?
                         ORDER BY timestamp''',
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

        def handle_update_glucose(self, record_id, data):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE glucose SET timestamp = ?, level = ? WHERE id = ?',
                          (data['timestamp'], data['level'], record_id))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_update_insulin(self, record_id, data):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE insulin SET timestamp = ?, level = ? WHERE id = ?',
                          (data['timestamp'], data['level'], record_id))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_update_intake(self, record_id, data):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT kcal_per_gram FROM nutrition WHERE id = ?',
                          (data['nutrition_id'],))
            result = cursor.fetchone()
            if not result:
                conn.close()
                self._set_headers(400)
                self.wfile.write(json.dumps({'error': 'Nutrition not found'}).encode())
                return
        
            kcal_per_gram = result[0]
            nutrition_kcal = data['nutrition_amount'] * kcal_per_gram
        
            cursor.execute('''UPDATE intake 
                             SET timestamp = ?, nutrition_id = ?, nutrition_amount = ?, nutrition_kcal = ?
                             WHERE id = ?''',
                          (data['timestamp'], data['nutrition_id'], 
                           data['nutrition_amount'], nutrition_kcal, record_id))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_update_supplements(self, record_id, data):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''UPDATE supplements 
                             SET timestamp = ?, supplement_name = ?, supplement_amount = ?
                             WHERE id = ?''',
                          (data['timestamp'], data['supplement_name'], 
                           data['supplement_amount'], record_id))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_update_event(self, record_id, data):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''UPDATE event 
                             SET timestamp = ?, event_name = ?, event_notes = ?
                             WHERE id = ?''',
                          (data['timestamp'], data['event_name'], 
                           data.get('event_notes', ''), record_id))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_update_nutrition(self, record_id, data):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''UPDATE nutrition 
                             SET nutrition_name = ?, kcal = ?, weight = ?
                             WHERE id = ?''',
                          (data['nutrition_name'], data['kcal'], data['weight'], record_id))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        # DELETE handlers
        def handle_delete_glucose(self, record_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM glucose WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_delete_insulin(self, record_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM insulin WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_delete_intake(self, record_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM intake WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_delete_supplements(self, record_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM supplements WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_delete_event(self, record_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM event WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
    
        def handle_delete_nutrition(self, record_id):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM nutrition WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            self._set_headers()
            self.wfile.write(json.dumps({'success': True}).encode())


    # UPDATE handlers
    def handle_update_glucose(self, record_id, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE glucose SET timestamp = ?, level = ? WHERE id = ?',
                      (data['timestamp'], data['level'], record_id))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_update_insulin(self, record_id, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE insulin SET timestamp = ?, level = ? WHERE id = ?',
                      (data['timestamp'], data['level'], record_id))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_update_intake(self, record_id, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT kcal_per_gram FROM nutrition WHERE id = ?',
                      (data['nutrition_id'],))
        result = cursor.fetchone()
        if not result:
            conn.close()
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': 'Nutrition not found'}).encode())
            return
    
        kcal_per_gram = result[0]
        nutrition_kcal = data['nutrition_amount'] * kcal_per_gram
    
        cursor.execute('''UPDATE intake 
                         SET timestamp = ?, nutrition_id = ?, nutrition_amount = ?, nutrition_kcal = ?
                         WHERE id = ?''',
                      (data['timestamp'], data['nutrition_id'], 
                       data['nutrition_amount'], nutrition_kcal, record_id))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_update_supplements(self, record_id, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''UPDATE supplements 
                         SET timestamp = ?, supplement_name = ?, supplement_amount = ?
                         WHERE id = ?''',
                      (data['timestamp'], data['supplement_name'], 
                       data['supplement_amount'], record_id))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_update_event(self, record_id, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''UPDATE event 
                         SET timestamp = ?, event_name = ?, event_notes = ?
                         WHERE id = ?''',
                      (data['timestamp'], data['event_name'], 
                       data.get('event_notes', ''), record_id))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_update_nutrition(self, record_id, data):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''UPDATE nutrition 
                         SET nutrition_name = ?, kcal = ?, weight = ?
                         WHERE id = ?''',
                      (data['nutrition_name'], data['kcal'], data['weight'], record_id))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    # DELETE handlers
    def handle_delete_glucose(self, record_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM glucose WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_delete_insulin(self, record_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM insulin WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_delete_intake(self, record_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM intake WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_delete_supplements(self, record_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM supplements WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_delete_event(self, record_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM event WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def handle_delete_nutrition(self, record_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM nutrition WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        self._set_headers()
        self.wfile.write(json.dumps({'success': True}).encode())


def main():
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found. Please run init_db.py first.")
        return
    
    # Enable SO_REUSEADDR to allow immediate server restart
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), GlucoseHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        httpd.serve_forever()

if __name__ == '__main__':
    main()
