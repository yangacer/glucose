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
- Dashboard endpoints (glucose chart, summary timesheet)
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

class TestGlucoseAPI(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start the server before running tests"""
        cls.test_db = 'test_glucose.db'
        cls.server_process = None
        
        # Create test database
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        
        # Modify server to use test database
        os.environ['DB_PATH'] = cls.test_db
        
        # Initialize test database
        conn = sqlite3.connect(cls.test_db)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE glucose (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            level INTEGER NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE insulin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            level REAL NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE nutrition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nutrition_name TEXT NOT NULL,
            kcal REAL NOT NULL,
            weight REAL NOT NULL,
            kcal_per_gram REAL GENERATED ALWAYS AS (kcal / weight) STORED
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE intake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nutrition_id INTEGER REFERENCES nutrition(id),
            timestamp DATETIME NOT NULL,
            nutrition_amount REAL NOT NULL,
            nutrition_kcal REAL NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE supplements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplement_name TEXT NOT NULL,
            default_amount REAL DEFAULT 1
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE supplement_intake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            supplement_id INTEGER REFERENCES supplements(id),
            supplement_amount REAL NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            event_name TEXT NOT NULL,
            event_notes TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        
        cls.host = 'localhost'
        cls.port = 8001  # Use different port for testing
        cls.base_url = f'http://{cls.host}:{cls.port}'
    
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
        if now.hour < 12:  # AM - previous is yesterday PM
            prev_time = (now - timedelta(days=1)).replace(hour=14, minute=0, second=0)
        else:  # PM - previous is today AM
            prev_time = now.replace(hour=8, minute=0, second=0)
        
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
        """Test glucose chart data endpoint"""
        today = datetime.now()
        start_date = f'{today.year}-01-01'
        end_date = f'{today.year}-12-31'
        
        status, response = self.make_request('GET', f'/api/dashboard/glucose-chart?start_date={start_date}&end_date={end_date}')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
    
    def test_17_get_summary_timesheet(self):
        """Test summary timesheet endpoint"""
        today = datetime.now()
        start_date = f'{today.year}-{today.month:02d}-01'
        end_date = today.strftime('%Y-%m-%d')
        
        status, response = self.make_request('GET', f'/api/dashboard/summary?start_date={start_date}&end_date={end_date}')
        self.assertEqual(status, 200)
        self.assertIsInstance(response, list)
    
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

def run_tests_with_server():
    """Run tests with a temporary test server"""
    print("Setting up test environment...")
    
    # Create test database
    test_db = 'test_glucose.db'
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Start server on test port with test database
    print("Starting test server on port 8001...")
    server_env = os.environ.copy()
    server_env['DB_PATH'] = test_db
    
    # Modify server.py temporarily to use test database
    with open('server.py', 'r') as f:
        server_code = f.read()
    
    server_code = server_code.replace("DB_PATH = 'glucose.db'", f"DB_PATH = '{test_db}'")
    server_code = server_code.replace("PORT = 8000", "PORT = 8001")
    
    with open('test_server_temp.py', 'w') as f:
        f.write(server_code)
    
    # Initialize test database using init_db logic
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE glucose (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level INTEGER NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX idx_glucose_timestamp ON glucose(timestamp)')
    
    cursor.execute('''
    CREATE TABLE insulin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        level REAL NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX idx_insulin_timestamp ON insulin(timestamp)')
    
    cursor.execute('''
    CREATE TABLE nutrition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nutrition_name TEXT NOT NULL,
        kcal REAL NOT NULL,
        weight REAL NOT NULL,
        kcal_per_gram REAL GENERATED ALWAYS AS (kcal / weight) STORED
    )
    ''')
    
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
    
    cursor.execute('''
    CREATE TABLE supplements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplement_name TEXT NOT NULL,
        default_amount REAL DEFAULT 1
    )
    ''')
    
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
    conn.close()
    
    # Start server
    server_process = subprocess.Popen(
        ['python3', 'test_server_temp.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        # Run tests
        print("\nRunning tests...\n")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestGlucoseAPI)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        server_process.terminate()
        server_process.wait()
        
        if os.path.exists('test_server_temp.py'):
            os.remove('test_server_temp.py')
        if os.path.exists(test_db):
            os.remove(test_db)

if __name__ == '__main__':
    success = run_tests_with_server()
    sys.exit(0 if success else 1)
