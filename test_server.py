#!/usr/bin/env python3
"""
Unit tests for glucose monitoring server API.

This test suite validates all API endpoints and database operations:
- Nutrition master data (CRUD)
- Supplements master data (CRUD)
- Glucose measurements (CRUD)
- Insulin doses (CRUD)
- Nutrition intake records (CRUD)
- Supplement intake records (CRUD)
- Event records (CRUD)
- Dashboard endpoints (glucose chart, summary timesheet, CV charts)
- Time-window queries (previous intake window)
- Date range filtering

The tests run against a temporary test database on port 8001.
"""

import unittest
import json
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from http.client import HTTPConnection
import time
import subprocess
from init_db import create_schema


class TestGlucoseAPI(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start the server before running tests"""
        cls.test_db = 'test_glucose.db'
        cls.port = 8001
        cls.host = 'localhost'
        cls.base_url = f'http://{cls.host}:{cls.port}'
        
        # Remove existing test database
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        
        # Create test database with schema (reusing init_db.py)
        conn = sqlite3.connect(cls.test_db)
        create_schema(conn)
        conn.close()
        
        # Configure and start server
        server_env = os.environ.copy()
        server_env['DB_PATH'] = cls.test_db
        server_env['PORT'] = str(cls.port)
        server_env['MTLS_ENABLED'] = 'false'
        
        print(f"Starting test server on port {cls.port}...")
        cls.server_process = subprocess.Popen(
            ['python3', 'server.py'],
            env=server_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # Wait for server to start with connection retry
        max_retries = 10
        for i in range(max_retries):
            time.sleep(0.5)
            try:
                conn = HTTPConnection(cls.host, cls.port, timeout=1)
                conn.request('GET', '/api/glucose')
                conn.getresponse()
                conn.close()
                print("Test server is ready.")
                break
            except:
                if i == max_retries - 1:
                    # Server failed to start, get error output
                    stdout, stderr = cls.server_process.communicate(timeout=1)
                    print(f"Server failed to start. stderr: {stderr.decode()}")
                    raise RuntimeError("Test server failed to start")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait()
        
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
    
    def make_request(self, method, path, data=None):
        """Helper method to make HTTP requests"""
        conn = HTTPConnection(self.host, self.port)
        headers = {'Content-Type': 'application/json'}
        
        body = json.dumps(data) if data else None
        conn.request(method, path, body, headers)
        
        response = conn.getresponse()
        response_data = response.read().decode()
        
        conn.close()
        
        return response.status, json.loads(response_data) if response_data else None
    
    def test_01_post_nutrition(self):
        """Test creating nutrition record"""
        data = {
            'nutrition_name': 'Apple',
            'kcal': 52,
            'weight': 100
        }
        
        status, response = self.make_request('POST', '/api/nutrition', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
    
    def test_02_get_nutrition_list(self):
        """Test retrieving nutrition list"""
        status, response = self.make_request('GET', '/api/nutrition')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        # Verify calculated kcal_per_gram
        apple = response[0]
        self.assertEqual(apple['nutrition_name'], 'Apple')
        self.assertAlmostEqual(apple['kcal_per_gram'], 0.52, places=2)
    
    def test_03_post_glucose(self):
        """Test creating glucose record"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'level': 95
        }
        
        status, response = self.make_request('POST', '/api/glucose', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
    
    def test_04_get_glucose_list(self):
        """Test retrieving glucose list"""
        status, response = self.make_request('GET', '/api/glucose')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        record = response[0]
        self.assertIn('id', record)
        self.assertIn('timestamp', record)
        self.assertIn('level', record)
        self.assertEqual(record['level'], 95)
    
    def test_05_post_insulin(self):
        """Test creating insulin record"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'level': 5.5
        }
        
        status, response = self.make_request('POST', '/api/insulin', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
    
    def test_06_get_insulin_list(self):
        """Test retrieving insulin list"""
        status, response = self.make_request('GET', '/api/insulin')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        record = response[0]
        self.assertAlmostEqual(record['level'], 5.5, places=1)
    
    def test_07_post_intake(self):
        """Test creating intake record"""
        # First get nutrition ID
        status, nutrition_list = self.make_request('GET', '/api/nutrition')
        nutrition_id = nutrition_list[0]['id']
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'nutrition_id': nutrition_id,
            'nutrition_amount': 150.0
        }
        
        status, response = self.make_request('POST', '/api/intake', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
        
        # Verify auto-calculated kcal
        self.assertIn('nutrition_kcal', response)
        expected_kcal = 150.0 * 0.52  # 150g * 0.52 kcal/g
        self.assertAlmostEqual(response['nutrition_kcal'], expected_kcal, places=1)
    
    def test_08_get_intake_list(self):
        """Test retrieving intake list"""
        status, response = self.make_request('GET', '/api/intake')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        record = response[0]
        self.assertEqual(record['nutrition_name'], 'Apple')
        self.assertAlmostEqual(record['nutrition_amount'], 150.0, places=1)
    
    def test_09_post_supplements(self):
        """Test creating supplement master record"""
        data = {
            'supplement_name': 'Vitamin C',
            'default_amount': 1000
        }
        
        status, response = self.make_request('POST', '/api/supplements', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
    
    def test_10_get_supplements_list(self):
        """Test retrieving supplements master list"""
        status, response = self.make_request('GET', '/api/supplements')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        record = response[0]
        self.assertEqual(record['supplement_name'], 'Vitamin C')
        self.assertEqual(record['default_amount'], 1000)
    
    def test_11_post_event(self):
        """Test creating event record"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'event_name': 'Morning walk',
            'event_notes': '30 minutes'
        }
        
        status, response = self.make_request('POST', '/api/event', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
    
    def test_12_get_event_list(self):
        """Test retrieving event list"""
        status, response = self.make_request('GET', '/api/event')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        record = response[0]
        self.assertEqual(record['event_name'], 'Morning walk')
        self.assertEqual(record['event_notes'], '30 minutes')
    
    def test_12a_post_supplement_intake(self):
        """Test creating supplement intake record"""
        # Get supplement ID
        status, supplement_list = self.make_request('GET', '/api/supplements')
        supplement_id = supplement_list[0]['id']
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'supplement_id': supplement_id,
            'supplement_amount': 500
        }
        
        status, response = self.make_request('POST', '/api/supplement-intake', data)
        self.assertEqual(status, 201)
        self.assertTrue(response.get('success'))
    
    def test_12b_get_supplement_intake_list(self):
        """Test retrieving supplement intake list"""
        status, response = self.make_request('GET', '/api/supplement-intake')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        
        record = response[0]
        self.assertEqual(record['supplement_name'], 'Vitamin C')
        self.assertEqual(record['supplement_amount'], 500)
    
    def test_13_update_glucose(self):
        """Test updating glucose record"""
        # Get existing record
        status, records = self.make_request('GET', '/api/glucose')
        record_id = records[0]['id']
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'level': 100
        }
        
        status, response = self.make_request('PUT', f'/api/glucose/{record_id}', data)
        self.assertEqual(status, 200)
        self.assertTrue(response.get('success'))
        
        # Verify update
        status, updated_records = self.make_request('GET', '/api/glucose')
        updated_record = next(r for r in updated_records if r['id'] == record_id)
        self.assertEqual(updated_record['level'], 100)
    
    def test_14_delete_glucose(self):
        """Test deleting glucose record"""
        # Create a new record to delete
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {'timestamp': timestamp, 'level': 80}
        self.make_request('POST', '/api/glucose', data)
        
        # Get the record
        status, records = self.make_request('GET', '/api/glucose')
        record_to_delete = records[0]
        record_id = record_to_delete['id']
        
        # Delete it
        status, response = self.make_request('DELETE', f'/api/glucose/{record_id}')
        self.assertEqual(status, 200)
        self.assertTrue(response.get('success'))
        
        # Verify deletion
        status, records_after = self.make_request('GET', '/api/glucose')
        deleted_exists = any(r['id'] == record_id for r in records_after)
        self.assertFalse(deleted_exists)
    
    def test_15_get_previous_window_intake(self):
        """Test getting previous time-window intake"""
        # Create intake in previous window
        now = datetime.now()
        if 5 <= now.hour < 17:  # Current is Day, previous is Night
            # Previous night window: 17:00 yesterday to 04:59 today
            prev_time = (now - timedelta(days=1)).replace(hour=20, minute=0, second=0)
        else:  # Current is Night (17:00-04:59), previous is Day
            if now.hour >= 17:  # Evening
                # Previous day window: 05:00 to 16:59 today
                prev_time = now.replace(hour=10, minute=0, second=0)
            else:  # Early morning (00:00-04:59)
                # Previous day window: 05:00 to 16:59 yesterday
                prev_time = (now - timedelta(days=1)).replace(hour=10, minute=0, second=0)
        
        # Get nutrition ID
        status, nutrition_list = self.make_request('GET', '/api/nutrition')
        nutrition_id = nutrition_list[0]['id']
        
        # Create intake in previous window
        data = {
            'timestamp': prev_time.strftime('%Y-%m-%d %H:%M:%S'),
            'nutrition_id': nutrition_id,
            'nutrition_amount': 100.0
        }
        self.make_request('POST', '/api/intake', data)
        
        # Get previous window intake
        status, response = self.make_request('GET', '/api/intake/previous-window')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, dict)
        self.assertIn('nutrition', response)
        self.assertIn('supplements', response)
        self.assertIsInstance(response['nutrition'], list)
        self.assertIsInstance(response['supplements'], list)
    
    def test_16_get_glucose_chart(self):
        """Test glucose chart data endpoint with both glucose and insulin series"""
        today = datetime.now()
        start_date = f'{today.year}-01-01'
        end_date = f'{today.year}-12-31'
        
        status, response = self.make_request('GET', f'/api/dashboard/glucose-chart?start_date={start_date}&end_date={end_date}')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        
        # Verify response structure if data exists
        if len(response) > 0:
            row = response[0]
            self.assertIn('week', row)
            self.assertIn('glucose_mean', row)
            self.assertIn('insulin_mean', row)
    
    def test_17_get_summary_timesheet(self):
        """Test summary timesheet endpoint with 12 glucose columns (+0 to +11)"""
        today = datetime.now()
        start_date = f'{today.year}-{today.month:02d}-01'
        end_date = today.strftime('%Y-%m-%d')
        
        status, response = self.make_request('GET', f'/api/dashboard/summary?start_date={start_date}&end_date={end_date}')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
        
        # Verify timesheet structure if data exists
        if len(response) > 0:
            row = response[0]
            self.assertIn('am_pm', row)
            self.assertIn('date', row)
            self.assertIn('dosage', row)
            self.assertIn('glucose_levels', row)
            self.assertIn('kcal_intake', row)
            
            # Verify glucose_levels has +0 to +11 (12 columns total)
            glucose_levels = row['glucose_levels']
            self.assertIn('+0', glucose_levels)
            for hour in range(1, 12):
                self.assertIn(f'+{hour}', glucose_levels)
            
            # Verify overlay data (not in main table)
            self.assertIn('dose_time', row)
            self.assertIn('intake_time', row)
            self.assertIn('nutrition', row)
            self.assertIn('grouped_supplements', row)
            self.assertIn('grouped_events', row)
    
    def test_18_filter_by_date_range(self):
        """Test filtering records by date range"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        status, response = self.make_request('GET', f'/api/glucose?start_date={start_date}&end_date={end_date}')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
    
    def test_19_invalid_nutrition_id(self):
        """Test creating intake with invalid nutrition ID"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'nutrition_id': 9999,  # Non-existent ID
            'nutrition_amount': 100.0
        }
        
        status, response = self.make_request('POST', '/api/intake', data)
        self.assertEqual(status, 400)
        self.assertIn('error', response)
    
    def test_20_update_supplement_master(self):
        """Test updating supplement master record"""
        # Get existing record
        status, records = self.make_request('GET', '/api/supplements')
        record_id = records[0]['id']
        
        data = {
            'supplement_name': 'Vitamin C 1000mg',
            'default_amount': 2000
        }
        
        status, response = self.make_request('PUT', f'/api/supplements/{record_id}', data)
        self.assertEqual(status, 200)
        self.assertTrue(response.get('success'))
        
        # Verify update
        status, updated_records = self.make_request('GET', '/api/supplements')
        updated_record = next(r for r in updated_records if r['id'] == record_id)
        self.assertEqual(updated_record['supplement_name'], 'Vitamin C 1000mg')
        self.assertEqual(updated_record['default_amount'], 2000)
    
    def test_21_update_supplement_intake(self):
        """Test updating supplement intake record"""
        # Get existing record
        status, records = self.make_request('GET', '/api/supplement-intake')
        record_id = records[0]['id']
        supplement_id = records[0]['supplement_id']
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'supplement_id': supplement_id,
            'supplement_amount': 1000
        }
        
        status, response = self.make_request('PUT', f'/api/supplement-intake/{record_id}', data)
        self.assertEqual(status, 200)
        self.assertTrue(response.get('success'))
        
        # Verify update
        status, updated_records = self.make_request('GET', '/api/supplement-intake')
        updated_record = next(r for r in updated_records if r['id'] == record_id)
        self.assertEqual(updated_record['supplement_amount'], 1000)
    
    def test_22_delete_supplement_intake(self):
        """Test deleting supplement intake record"""
        # Create a new record to delete
        status, supplement_list = self.make_request('GET', '/api/supplements')
        supplement_id = supplement_list[0]['id']
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'timestamp': timestamp,
            'supplement_id': supplement_id,
            'supplement_amount': 250
        }
        self.make_request('POST', '/api/supplement-intake', data)
        
        # Get the record
        status, records = self.make_request('GET', '/api/supplement-intake')
        record_to_delete = records[0]
        record_id = record_to_delete['id']
        
        # Delete it
        status, response = self.make_request('DELETE', f'/api/supplement-intake/{record_id}')
        self.assertEqual(status, 200)
        self.assertTrue(response.get('success'))
        
        # Verify deletion
        status, records_after = self.make_request('GET', '/api/supplement-intake')
        deleted_exists = any(r['id'] == record_id for r in records_after)
        self.assertFalse(deleted_exists)
    
    def test_23_cv_calculation(self):
        """Test CV calculation function"""
        from server import calculate_cv
        from datetime import datetime
        
        test_data = [
            (datetime(2026, 2, 20, 8, 0), 100),
            (datetime(2026, 2, 20, 9, 0), 110),
            (datetime(2026, 2, 20, 10, 0), 105),
            (datetime(2026, 2, 20, 11, 0), 95),
        ]
        
        cv = calculate_cv(test_data)
        self.assertIsNotNone(cv)
        self.assertGreater(cv, 0)
        self.assertIsInstance(cv, float)
    
    def test_24_generate_cv_windows(self):
        """Test CV window generation"""
        from server import generate_cv_windows
        from datetime import date
        
        end_date = date(2026, 2, 26)
        
        windows_12h = generate_cv_windows(end_date, 7, 12)
        self.assertGreater(len(windows_12h), 0)
        self.assertEqual(len(windows_12h), 14)
        
        windows_48h = generate_cv_windows(end_date, 30, 48)
        self.assertGreater(len(windows_48h), 0)
        
        windows_5d = generate_cv_windows(end_date, 30, 120)
        self.assertGreater(len(windows_5d), 0)
    
    def test_25_cv_charts_api(self):
        """Test CV charts API endpoint"""
        status, data = self.make_request('GET', '/api/dashboard/cv-charts?end_date=2026-02-26')
        self.assertEqual(status, 200)
        
        self.assertIn('cv_7d_12h', data)
        self.assertIn('cv_30d_48h', data)
        self.assertIn('cv_30d_5d', data)
        
        for window in data['cv_7d_12h']:
            self.assertIn('label', window)
            self.assertIn('cv', window)
        
        self.assertIsInstance(data['cv_7d_12h'], list)
        self.assertIsInstance(data['cv_30d_48h'], list)
        self.assertIsInstance(data['cv_30d_5d'], list)
    
    def test_26_risk_metrics_calculation(self):
        """Test LBGI, HBGI, ADRR calculation functions"""
        from server import calculate_lbgi, calculate_hbgi, calculate_adrr
        from datetime import datetime
        
        test_data = [
            (datetime(2026, 2, 20, 8, 0), 100),
            (datetime(2026, 2, 20, 9, 0), 110),
            (datetime(2026, 2, 20, 10, 0), 105),
            (datetime(2026, 2, 20, 11, 0), 95),
        ]
        
        lbgi = calculate_lbgi(test_data)
        self.assertIsNotNone(lbgi)
        self.assertGreaterEqual(lbgi, 0)
        self.assertIsInstance(lbgi, float)
        
        hbgi = calculate_hbgi(test_data)
        self.assertIsNotNone(hbgi)
        self.assertGreaterEqual(hbgi, 0)
        self.assertIsInstance(hbgi, float)
        
        test_rows = [
            ('2026-02-20 08:00:00', 100),
            ('2026-02-20 09:00:00', 110),
            ('2026-02-20 10:00:00', 105),
            ('2026-02-20 11:00:00', 95),
        ]
        windows = [('test', '2026-02-20 00:00:00', '2026-02-20 23:59:59')]
        
        adrr = calculate_adrr(test_rows, windows)
        self.assertIsNotNone(adrr)
        self.assertGreaterEqual(adrr, 0)
        self.assertIsInstance(adrr, float)
    
    def test_27_risk_metrics_api(self):
        """Test risk metrics API endpoint"""
        status, data = self.make_request('GET', '/api/dashboard/risk-metrics?end_date=2026-02-26')
        self.assertEqual(status, 200)
        
        # Check all LBGI charts
        self.assertIn('lbgi_7d_12h', data)
        self.assertIn('lbgi_30d_48h', data)
        self.assertIn('lbgi_30d_5d', data)
        
        # Check all HBGI charts
        self.assertIn('hbgi_7d_12h', data)
        self.assertIn('hbgi_30d_48h', data)
        self.assertIn('hbgi_30d_5d', data)
        
        # Check all ADRR charts
        self.assertIn('adrr_7d_12h', data)
        self.assertIn('adrr_30d_48h', data)
        self.assertIn('adrr_30d_5d', data)
        
        # Verify structure
        for window in data['lbgi_7d_12h']:
            self.assertIn('label', window)
            self.assertIn('value', window)
        
        self.assertIsInstance(data['lbgi_7d_12h'], list)
        self.assertIsInstance(data['hbgi_7d_12h'], list)
        self.assertIsInstance(data['adrr_7d_12h'], list)


if __name__ == '__main__':
    unittest.main(verbosity=2)
