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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
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
        
        # Get all intakes within date range
        cursor.execute('''SELECT i.id, i.timestamp, i.nutrition_kcal, n.nutrition_name
                         FROM intake i
                         JOIN nutrition n ON i.nutrition_id = n.id
                         WHERE i.timestamp BETWEEN ? AND ?
                         ORDER BY i.timestamp''',
                      (start_date, end_date + ' 23:59:59'))
        intakes = cursor.fetchall()
        
        summary_data = []
        for intake_id, intake_time, kcal, nutrition_name in intakes:
            intake_dt = datetime.strptime(intake_time, '%Y-%m-%d %H:%M:%S')
            
            # Get insulin dose nearest in time to intake (before or after)
            cursor.execute('''
                SELECT timestamp, level, ABS(julianday(timestamp) - julianday(?)) as time_diff
                FROM insulin
                ORDER BY time_diff ASC
                LIMIT 1
            ''', (intake_time,))
            insulin_row = cursor.fetchone()
            dose_time = insulin_row[0] if insulin_row else None
            dosage = insulin_row[1] if insulin_row else None
            
            # Get glucose levels before and after intake (hourly for 12 hours)
            glucose_levels = {}
            
            # Before intake
            cursor.execute('''SELECT level FROM glucose
                             WHERE timestamp <= ?
                             ORDER BY timestamp DESC LIMIT 1''',
                          (intake_time,))
            before_row = cursor.fetchone()
            glucose_levels['before'] = before_row[0] if before_row else None
            
            # After intake (+1hr to +12hr)
            for hour in range(1, 13):
                target_time = intake_dt + timedelta(hours=hour)
                target_str = target_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Get average glucose in ±30min window
                window_start = (target_time - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                window_end = (target_time + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''SELECT AVG(level) FROM glucose
                                 WHERE timestamp BETWEEN ? AND ?''',
                              (window_start, window_end))
                avg_row = cursor.fetchone()
                glucose_levels[f'+{hour}hr'] = round(avg_row[0], 1) if avg_row[0] else None
            
            # Get events within 12 hours
            end_time = (intake_dt + timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''SELECT event_name FROM event
                             WHERE timestamp BETWEEN ? AND ?
                             ORDER BY timestamp''',
                          (intake_time, end_time))
            events = cursor.fetchall()
            grouped_events = ', '.join([e[0] for e in events]) if events else ''
            
            summary_data.append({
                'am_pm': 'AM' if intake_dt.hour < 12 else 'PM',
                'date': intake_dt.strftime('%Y-%m-%d'),
                'dose_time': dose_time,
                'intake_time': intake_time,
                'dosage': dosage,
                'nutrition': nutrition_name,
                'glucose_levels': glucose_levels,
                'kcal_intake': kcal,
                'grouped_events': grouped_events
            })
        
        conn.close()
        
        self._set_headers()
        self.wfile.write(json.dumps(summary_data).encode())

def main():
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found. Please run init_db.py first.")
        return
    
    with socketserver.TCPServer(("", PORT), GlucoseHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        httpd.serve_forever()

if __name__ == '__main__':
    main()
