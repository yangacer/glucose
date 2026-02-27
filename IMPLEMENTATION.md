# Glucose Monitoring Dashboard - Implementation Guide

## Overview

This document describes the technical implementation details for developers. For feature specifications and UI/UX design, see `DESIGN.md`.

---

# Architecture

**Pattern:** Traditional server-side web application with REST API

**Components:**
- `server.py`: HTTP server with REST API endpoints and business logic
- `init_db.py`: Database schema management
- `static/`: Frontend HTML/CSS/JavaScript
- `test_server.py`: Test suite

---

# Database

## Schema Management

**File:** `init_db.py`

**Key Function:** `create_schema(conn)`
- Single source of truth for database schema
- Used by both production initialization and test setup
- Creates all tables with indexes

**Schema includes:**
- 7 tables: glucose, insulin, nutrition, intake, supplements, supplement_intake, event
- Indexes on all timestamp columns for query performance
- Foreign key indexes for JOIN operations
- Generated column for kcal_per_gram calculation

---

## Connection Management

**File:** `server.py`

**Pattern:** Context manager with automatic cleanup

```python
@contextmanager
def get_db_connection():
    # Yields connection, automatically closes on exit/exception
```

**Usage:** All database operations use `with get_db_connection() as conn:`

**Benefits:**
- Prevents connection leaks
- Exception-safe cleanup
- No manual close() calls

**Design Decision:** No connection pooling - single connection per request is sufficient for low-traffic personal app.

---

## Indexing Strategy

**Approach:** Full timestamp indexes (not date-part)

**Rationale:**
- All queries use `BETWEEN` with full datetime strings
- SQLite B-tree efficiently handles ISO8601 string prefix matching
- No overhead from function calls like `DATE(timestamp)`
- Supports both range and point queries

**Query Performance:**
- BETWEEN queries: O(log n + k) where k = matching rows
- ORDER BY timestamp: Uses index, no additional sorting
- Filtered queries with LIMIT: O(log n)

---

# Business Logic

## Core Algorithms

**File:** `server.py`

### Time-Weighted Mean
- **Function:** `calculate_time_weighted_mean(data)`
- **Algorithm:** Trapezoidal rule integration
- **Formula:** `Σ((v0 + v1) / 2 × Δt) / total_time`
- **Used by:** CV calculation, glucose/insulin charts

### Coefficient of Variation (CV)
- **Function:** `calculate_cv(data)`
- **Formula:** `(Standard Deviation / Time-Weighted Mean) × 100`
- **Dependencies:** `calculate_standard_deviation()`, `calculate_time_weighted_mean()`

### Risk Metrics
- **Functions:** `calculate_lbgi()`, `calculate_hbgi()`, `calculate_adrr()`
- **Base function:** `calculate_risk_function(glucose)` - transforms glucose to symmetrical risk scale
- **Formula:** `f(G) = 1.509 × (ln(G)^1.084 - 5.381)`
- **LBGI:** Averages low-risk values where f(G) < 0
- **HBGI:** Averages high-risk values where f(G) > 0
- **ADRR:** Groups by calendar day, sums LBGI + HBGI per day, averages across days

### Window Generation
- **Function:** `generate_cv_windows(end_date, days, window_hours)`
- **Anchor:** 5:00 AM on end_date
- **Direction:** Walks backward creating fixed-size non-overlapping windows
- **Labeling:** Different formats for 12h, 48h, and 120h windows

---

# API Endpoints

## Structure

**File:** `server.py` class `GlucoseRequestHandler`

**Routing:** Dictionary-based routing in `do_GET()` method

**Pattern:**
```python
route_handlers = {
    '/api/endpoint': lambda: self.handle_method(query_params),
}
```

## Endpoint Categories

### Data Input (POST)
- `/api/glucose` - Create glucose measurement
- `/api/insulin` - Create insulin dose
- `/api/intake` - Create nutrition intake (auto-calculates kCal)
- `/api/supplement-intake` - Create supplement intake
- `/api/event` - Create event
- `/api/nutrition` - Create nutrition master
- `/api/supplements` - Create supplement master

### Data Retrieval (GET)
- `/api/glucose` - List with optional date filters
- `/api/insulin` - List with optional date filters
- `/api/intake` - List with optional date filters
- `/api/supplement-intake` - List with optional date filters
- `/api/event` - List with optional date filters
- `/api/nutrition` - List all nutrition master
- `/api/supplements` - List all supplement master
- `/api/intake/previous-window` - Get intake from previous 12h window

### Data Updates (PUT)
- `/api/glucose/{id}` - Update glucose record
- `/api/insulin/{id}` - Update insulin record
- `/api/intake/{id}` - Update intake record
- `/api/supplement-intake/{id}` - Update supplement intake
- `/api/supplements/{id}` - Update supplement master
- `/api/event/{id}` - Update event record
- `/api/nutrition/{id}` - Update nutrition master

### Data Deletion (DELETE)
- `/api/glucose/{id}` - Delete glucose record
- `/api/insulin/{id}` - Delete insulin record
- `/api/intake/{id}` - Delete intake record
- `/api/supplement-intake/{id}` - Delete supplement intake
- `/api/supplements/{id}` - Delete supplement master
- `/api/event/{id}` - Delete event record
- `/api/nutrition/{id}` - Delete nutrition master

### Dashboard (GET)
- `/api/dashboard/glucose-chart` - Weekly glucose/insulin averages
- `/api/dashboard/summary` - Summary timesheet data
- `/api/dashboard/cv-charts` - CV data for 3 time windows
- `/api/dashboard/risk-metrics` - LBGI/HBGI/ADRR for 3 time windows

---

# Frontend Architecture

## Module Organization

**Files in `static/js/`:**
- `config.js` - API base URL configuration
- `utils.js` - Common utilities (timestamp formatting, date initialization)
- `dashboard.js` - Chart rendering and dashboard loading
- `forms.js` - Form submission handlers
- `dynamic-items.js` - Dynamic add/remove for intake form
- `audit.js` - Audit/edit listing rendering
- `tabs.js` - Tab navigation
- `main.js` - Application initialization

## Key Patterns

### Chart Rendering
- Store chart instances globally to enable destroy/recreate
- Consistent configuration across similar chart types
- `drawTime: 'beforeDatasetsDraw'` for threshold bands
- Reusable rendering functions with parameters for thresholds

### Data Loading
- Async/await for API calls
- Error handling with console.error
- Date input initialization on page load
- Auto-refresh on filter changes

### Form Handling
- Timestamp auto-fill with current time
- "Reset to Now" buttons for quick updates
- Dynamic item management (nutrition/supplement lists)
- Validation before submission

---

# mTLS Security

## Implementation

**File:** `server.py`

**Environment Variables:**
- `MTLS_ENABLED` - Toggle mTLS (default: true)
- `CA_CERT`, `SERVER_CERT`, `SERVER_KEY` - Certificate paths

**Functions:**
- `create_ssl_context()` - Sets up SSL with client cert verification
- `check_certificate_expiration()` - Warns if cert expiring soon
- `log_client_certificate()` - Logs client CN on connection

**Certificate Requirements:**
- CA cert: `certs/ca/ca-cert.pem`
- Server cert: `certs/server/server-cert.pem`
- Server key: `certs/server/server-key.pem`
- Client certs: `certs/clients/client-*-cert.pem`

**Security Settings:**
- `ssl.CERT_REQUIRED` - Mandatory client certificate
- TLS 1.2+ minimum version
- Directory listing disabled (403 Forbidden)

## Certificate Generation

**Script:** `generate-certs.sh`

**Steps:**
1. Generate CA key and self-signed certificate (10 year validity)
2. Generate server key and CSR, sign with CA (2 year validity)
3. Generate client key and CSR, sign with CA (1 year validity)
4. Create PKCS#12 files for browser import

**Options:**
- Interactive mode (prompts for details)
- Auto mode (uses defaults)
- Client-only mode (generates additional clients)

---

# Testing

## Test Structure

**File:** `test_server.py`

**Key Improvements:**
- Reuses `init_db.create_schema()` - no duplicate schema code
- Uses standard `unittest.TestCase` with `setUpClass`/`tearDownClass`
- Context managers ensure cleanup
- Connection retry for server startup

**Test Execution:**
1. `setUpClass`: Creates test DB, starts server on port 8001
2. Tests run in numbered order (test_01 through test_29)
3. `tearDownClass`: Stops server, removes test DB

**Test Coverage:**
- 29 tests covering all API endpoints
- Unit tests for calculation functions
- Integration tests for dashboard endpoints
- Error handling validation

---

# Development Workflow

## Adding New Features

1. **Update schema:** Modify `init_db.create_schema()` if new tables needed
2. **Add business logic:** Add calculation functions to `server.py`
3. **Create API endpoint:** Add route and handler to `server.py`
4. **Update frontend:** Add UI elements to `index.html`, logic to appropriate JS file
5. **Write tests:** Add test cases to `test_server.py`
6. **Update docs:** Update `DESIGN.md` (feature) and this file (implementation)

## Testing Changes

```bash
# Run all tests
python3 test_server.py

# Test specific functionality manually
MTLS_ENABLED=false PORT=8000 python3 server.py
```

## Common Patterns

**Adding a new chart:**
1. Create API endpoint returning `[{"label": str, "value": float}]` format
2. Add canvas element to `index.html`
3. Create render function in `dashboard.js` following CV/risk metric patterns
4. Call render function from `loadDashboard()`

**Adding a new input form:**
1. Add section to `index.html` with form and audit table
2. Create POST handler in `server.py`
3. Add form submission handler in `forms.js`
4. Add audit listing in `audit.js`
5. Add date input initialization in `utils.js`

---

# Design Decisions

## Why Python (not Rust)?
- Rapid development for statistical calculations
- No performance bottleneck (tests run in ~0.7s)
- Easy deployment without compilation
- Clear, readable analytics code
- Data collection is bottleneck, not computation

## Why No SQL for Complex Calculations?
- Time-weighted mean (trapezoidal rule) very complex in SQL
- Risk metrics require logarithms and conditional branching
- SQLite lacks advanced statistical functions
- Python code is testable and maintainable
- Query raw data once, process in memory

## Why Context Managers?
- Exception-safe resource cleanup
- Prevents connection leaks
- Standard Python pattern
- More important than connection pooling for low-traffic app

## Why Separate CV and Risk Metrics?
- Different scales (CV: 0-40%, ADRR: 0-80+)
- Different meanings (relative variability vs absolute risk)
- Clinical interpretation requires seeing them separately
- Different threshold values for each metric

## Why Threshold Bands Behind Lines?
- Lines and data points must be clearly visible
- Bands provide context without obscuring data
- Chart.js `drawTime: 'beforeDatasetsDraw'` enables this
- Consistent alpha (0.3) for subtle but visible bands

---

# Troubleshooting

## Tests Failing
- Check if port 8001 is available: `lsof -i :8001`
- Ensure init_db.py has no syntax errors
- Verify test DB is deleted between runs

## Server Won't Start
- Check certificates exist if MTLS_ENABLED=true
- Verify port is not in use
- Check DB_PATH points to valid location

## Charts Not Rendering
- Check browser console for JavaScript errors
- Verify Chart.js and annotation plugin are loaded
- Ensure canvas elements have unique IDs
- Check API endpoints return correct JSON format

## Connection Errors
- Verify context manager is used: `with get_db_connection() as conn:`
- Check no manual `conn.close()` remains after `with` blocks
- Ensure `execute_query()` uses context manager internally

---

# Maintenance

## Schema Changes
1. Update `init_db.create_schema()` function
2. Migration script may be needed for existing databases
3. Run tests to verify compatibility

## Adding Indexes
- Add to `create_schema()` function
- Document rationale in this file
- Analyze query performance if needed

## Certificate Renewal
```bash
# Regenerate all certificates
./generate-certs.sh

# Distribute new client certificates to users
# Update server and restart
```

## Performance Monitoring
```bash
# Check index usage
sqlite3 glucose.db "EXPLAIN QUERY PLAN SELECT * FROM glucose WHERE timestamp BETWEEN ? AND ?;"

# Analyze database
sqlite3 glucose.db "ANALYZE;"
```

---

# References

- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Chart.js**: https://www.chartjs.org/docs/
- **Chart.js Annotation Plugin**: https://www.chartjs.org/chartjs-plugin-annotation/
- **Python contextlib**: https://docs.python.org/3/library/contextlib.html
- **mTLS Guide**: See `CLIENT.md` for client setup instructions
