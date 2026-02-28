# Glucose Monitoring Dashboard - Implementation Guide

## Overview

This document describes the technical implementation details for developers. For feature specifications and UI/UX design, see `DESIGN.md`.

**Target Species:** Cats - all threshold values are calibrated for feline glucose metabolism.

---

# Architecture

**Pattern:** Multi-threaded server-side web application with REST API

**Components:**
- `server.py`: HTTP server with REST API endpoints and business logic
- `init_db.py`: Database schema management
- `static/`: Frontend HTML/CSS/JavaScript
- `test_server.py`: Test suite

**Threading Model:**
- Uses `socketserver.ThreadingTCPServer` for concurrent request handling
- Each request handled in separate daemon thread
- Prevents one slow request from blocking others
- Threads automatically cleaned up when request completes

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
- `utils.js` - Common utilities (timestamp formatting, date initialization, message display, button states)
- `dashboard.js` - Chart rendering and dashboard loading
- `forms.js` - Form submission handlers with loading states
- `dynamic-items.js` - Dynamic add/remove for intake form (nutrition and supplements)
- `audit.js` - Audit/edit listing rendering
- `tabs.js` - Tab navigation
- `main.js` - Application initialization

**Dependency Order:**
- Defined in `static/index.html.dev` as single source of truth
- Must load in order: config → utils → tabs/dashboard/etc → main
- `build-js.py` extracts order from `index.html.dev` automatically

## Development vs Production

**Development Mode (`MTLS_ENABLED=false`):**
- Server serves `static/index.html.dev`
- Individual JS files loaded separately (unminified)
- Easy debugging with readable code and line numbers
- No build step required during development
- Fast iteration: edit JS → refresh browser

**Production Mode (`MTLS_ENABLED=true`):**
- Server serves `static/index.html`
- Single minified bundle `js/release/app.min.js?v=x.y.z`
- Optimized for performance and caching
- Built with `./build-js.py`

**Build Process:**
```bash
# Generate minified bundle from current version
./build-js.py

# Or bump version
./build-js.py 0.6.0
```

**Build script (`build-js.py`):**
1. Reads script order from `static/index.html.dev`
2. Scans `static/js/` for `*.js` files (excludes `*.min.js` and chart files)
3. Combines files in dependency order
4. Minifies with terser
5. Generates `static/index.html` with versioned script tag

**Key Files:**
- `static/index.html.dev` - Development HTML (single source of truth for script order)
- `static/index.html` - Production HTML (auto-generated)
- `static/js/release/app.min.js` - Minified bundle (auto-generated)
- `build-js.py` - Build script

See `DEPLOY.md` for detailed workflow documentation.

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
- Visual feedback with loading states and animations
- Submit button state management (loading, disabled, spinner)
- Error and success message display with animations
- Prevention of double-submission through button disabling

---

# UI Components & Visual Feedback

## User Feedback System

**Purpose:** Provide clear, immediate visual feedback for all user actions, especially form submissions.

**Implementation:** Enhanced CSS animations and JavaScript state management.

### Message Display

**File:** `static/js/utils.js`

**Function:** `showMessage(elementId, success, message)`

**Behavior:**
1. Clears previous message state
2. Sets message text and class (success/error)
3. Triggers fade-in animation (10ms delay for CSS transition)
4. Displays message for timeout duration
5. Fades out and removes message

**Timeouts:**
- Success: 5 seconds
- Error: 8 seconds (60% longer for readability)

**CSS Classes:**
- `.message` - Base styling with fade transition
- `.message.show` - Visible state (opacity: 1, translateY: 0)
- `.message.success` - Green background, checkmark icon
- `.message.error` - Red background, X icon, shake animation

### Submit Button States

**Functions:**
- `setButtonLoading(button, loadingText)` - Disables button, shows loading state
- `resetButton(button)` - Restores button to original state

**Loading State Features:**
- Text changes to "Submitting..." (customizable)
- Button disabled (`disabled = true`)
- Background grays out (`#9ca3af`)
- Cursor changes to "wait"
- Animated spinner appears (CSS `::after` pseudo-element)
- Original text stored in `data-originalText` attribute

**CSS Classes:**
- `.submitting` - Loading state styling
- `::after` - Rotating spinner animation (16px, right-aligned)

### Animations

**Shake Animation (Errors Only):**
```css
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 30%, 50%, 70%, 90% { transform: translateX(-8px); }
    20%, 40%, 60%, 80% { transform: translateX(8px); }
}
```
- Duration: 0.4 seconds
- Oscillation: ±8px horizontal
- Applied automatically to error messages

**Spinner Animation (Button Loading):**
```css
@keyframes spinner {
    to { transform: rotate(360deg); }
}
```
- Duration: 0.6 seconds linear loop
- Applied to button `::after` pseudo-element
- 16px diameter, white border with transparent top

**Fade Transitions:**
- Fade-in: 0.3s opacity + translateY
- Fade-out: 0.3s opacity (message hidden after 300ms)

## Dynamic Form Items

**File:** `static/js/dynamic-items.js`

**Purpose:** Manage add/remove of nutrition and supplement items in intake form.

### Key Features:

**Nutrition Items:**
- Always require at least one item
- Remove button hidden on last item
- Automatic renumbering after removal
- Event listeners attached dynamically

**Supplement Items:**
- Can remove ALL items (optional supplements) - **v0.7.0**
- Remove button always visible
- Supports zero supplement submissions
- Initial item event listener in `initializeDynamicItems()`

**Functions:**
- `addNutritionItem()` - Adds new nutrition row
- `addSupplementItem()` - Adds new supplement row
- `updateNutritionRemoveButtons()` - Shows/hides remove buttons
- `updateSupplementRemoveButtons()` - Always shows remove buttons
- `renumberNutritionItems()` - Updates item numbers after removal
- `renumberSupplementItems()` - Updates supplement numbers after removal

**Change in v0.7.0:**
```javascript
// OLD: Only show when multiple items
removeBtn.style.display = items.length > 1 ? 'inline-block' : 'none';

// NEW: Always show (allow removing all)
removeBtn.style.display = 'inline-block';
```

## Form Submission Flow

**Pattern:** All forms follow consistent submission pattern

**Example Flow (Glucose Form):**
```javascript
async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn);  // Show loading state
    
    // Prepare data
    const data = { /* ... */ };
    
    // Submit to API
    const result = await submitData('/glucose', data);
    
    resetButton(submitBtn);  // Restore button
    showMessage('glucose-message', result.success, result.message);
    
    if (result.success) {
        e.target.reset();
        loadGlucoseAudit();
    }
}
```

**Applied to Forms:**
- Glucose, Insulin, Event, Nutrition, Supplements (simple forms)
- Intake form (complex multi-item with special handling)

**Error Handling:**
- Network errors caught and displayed
- Validation errors from server shown with shake
- Button always reset (success or failure)
- Try-catch blocks ensure button state restored

## CSS Structure

**File:** `static/css/styles.css`

**Message Styles:**
- `.message` - Base: padding, border-radius, initial opacity 0
- `.message.show` - Visible: opacity 1, translateY(0)
- `.message.success` - Green: #d4edda bg, #155724 text, ✓ icon
- `.message.error` - Red: #f8d7da bg, #721c24 text, ✖ icon, shake

**Button Styles:**
- `form button[type="submit"]` - Base styling with transition
- `button:disabled` - Gray background, not-allowed cursor
- `button.submitting` - Loading state with spinner
- `button.submitting::after` - Spinner pseudo-element

**Design Tokens:**
| Element | Color | Usage |
|---------|-------|-------|
| Success bg | #d4edda | Light green background |
| Success text | #155724 | Dark green text |
| Success border | #c3e6cb | Medium green border |
| Error bg | #f8d7da | Light red background |
| Error text | #721c24 | Dark red text |
| Error border | #f5c6cb | Medium red border |
| Loading bg | #9ca3af | Gray for disabled state |

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

# Test in development mode (unminified JS)
MTLS_ENABLED=false PORT=8000 python3 server.py

# Test in production mode (minified JS)
# First build the bundle:
./build-js.py
# Then start server:
MTLS_ENABLED=true PORT=8443 python3 server.py
```

## Common Patterns

**Adding a new chart:**
1. Create API endpoint returning `[{"label": str, "value": float}]` format
2. Add canvas element to `index.html.dev`
3. Create render function in `dashboard.js` following CV/risk metric patterns
4. Call render function from `loadDashboard()`
5. Run `./build-js.py` to regenerate production HTML

**Adding a new input form:**
1. Add section to `index.html.dev` with form and audit table
2. Add message div: `<div id="formname-message" class="message"></div>`
3. Create POST handler in `server.py`
4. Add form submission handler in `forms.js`:
   - Get submit button: `const submitBtn = e.target.querySelector('button[type="submit"]')`
   - Set loading: `setButtonLoading(submitBtn)`
   - Submit data with error handling
   - Reset button: `resetButton(submitBtn)`
   - Show message: `showMessage('formname-message', success, message)`
5. Add audit listing in `audit.js`
6. Add date input initialization in `utils.js` if needed
7. Run `./build-js.py` to regenerate production HTML

**Adding visual feedback to existing form:**
1. Locate form submission handler in `forms.js`
2. Add button state management:
   ```javascript
   const submitBtn = e.target.querySelector('button[type="submit"]');
   setButtonLoading(submitBtn);
   // ... existing logic ...
   resetButton(submitBtn);
   ```
3. Ensure error handling includes button reset
4. Use `showMessage()` for all success/error feedback

**Adding dynamic items (like supplements):**
1. Create container in HTML: `<div id="items-container"></div>`
2. Add functions in `dynamic-items.js`:
   - `addItem()` - Create new item with remove button
   - `updateRemoveButtons()` - Show/hide based on rules
   - `renumberItems()` - Update labels after removal
3. Attach event listeners in `initializeDynamicItems()`
4. For optional items: always show remove button
5. For required items: hide when count = 1

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

## Feline-Specific Thresholds
**Why different from human values?**
- Cats have naturally higher glucose baseline (70-150 mg/dL vs human 70-100 mg/dL)
- Greater glucose variability is normal in cats
- Diabetic cats tolerate wider ranges (100-250 mg/dL target)
- Risk metric formulas adapted for feline physiology

**Threshold Values:**
- CV: 0-25% (green), 25-35% (yellow), >35% (red)
- LBGI: 0-3.5 (green), 3.5-7 (yellow), >7 (red)
- HBGI: 0-6 (green), 6-12 (yellow), >12 (red)
- ADRR: 0-25 (green), 25-50 (yellow), >50 (red)

**Note:** These values are adjusted from human clinical thresholds based on feline glucose metabolism research and veterinary guidelines.

## UI Feedback Design

**Why shake animation for errors?**
- Human attention drawn to motion - makes errors impossible to miss
- Horizontal shake is universally recognized as "no/error"
- Short duration (0.4s) doesn't feel distracting
- Combined with color/icon for redundant signaling

**Why longer timeout for errors (8s vs 5s)?**
- Error messages often contain technical details needing reading time
- Users need time to understand what went wrong
- Success messages are simple and need less reading time
- 60% increase (3 seconds) is perceptually significant

**Why disable button during submission?**
- Prevents double-submission (critical for data integrity)
- Clear visual feedback that action is in progress
- Matches user expectations from modern web apps
- Gray color universally understood as "inactive"

**Why use icons (✓/✖)?**
- Language-agnostic communication
- Instant recognition without reading text
- Adds visual weight to messages
- Improves accessibility (redundant signaling)

**Why CSS animations over JavaScript?**
- Better performance (GPU accelerated)
- Smoother 60fps animations
- Less CPU usage
- Declarative and easier to maintain
- Works even if JavaScript is slow/blocked

**Why pseudo-elements for icons?**
- No additional HTML elements needed
- Automatic styling inheritance
- Easy to override per message type
- Cleaner markup separation
- Unicode icons work everywhere

---

# Troubleshooting

## Server Stops Responding / Page Hangs

**Symptoms:**
- Browser loading indefinitely
- No error messages
- Server process still running but unresponsive

**Root Causes & Fixes:**

**1. Single-threaded server (FIXED)**
- **Problem:** `TCPServer` handles one request at a time
- **Solution:** Now uses `ThreadingTCPServer` for concurrent requests
- **Impact:** One slow/hanging request won't block others

**2. Unhandled exceptions (FIXED)**
- **Problem:** Exception in request handler leaves client waiting forever
- **Solution:** All HTTP methods (GET/POST/PUT/DELETE) now have try-except
- **Impact:** Errors return 500 response instead of hanging

**3. Database connection leaks (FIXED)**
- **Problem:** Unclosed connections could exhaust SQLite resources
- **Solution:** Context managers ensure cleanup even on exceptions
- **Impact:** Connections always released properly

**4. JSON parsing errors (FIXED)**
- **Problem:** Malformed JSON in POST/PUT causes uncaught exception
- **Solution:** Separate try-except for JSON parsing returns 400 error
- **Impact:** Client receives clear error message

**Diagnostic Steps:**
```bash
# Check server logs for exceptions
tail -f server.log  # if logging to file

# Check which requests are being processed
# Look for timestamps in console output

# Test with curl to isolate browser issues
curl -v http://localhost:8000/api/glucose

# Check database locks
sqlite3 glucose.db "PRAGMA busy_timeout;"
```

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

## JavaScript Updates

**During development:**
1. Edit JS files in `static/js/`
2. Test with `MTLS_ENABLED=false` (uses `index.html.dev`)
3. No build step needed

**Before production deployment:**
1. Update version: `./build-js.py <new_version>`
2. Test with `MTLS_ENABLED=true` to verify minified bundle
3. Commit both `index.html.dev` and generated `index.html`

**Changing script dependency order:**
1. Edit `static/index.html.dev` (single source of truth)
2. Run `./build-js.py` to regenerate bundle
3. Test both dev and prod modes

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

# Version History

## v0.7.0 (2026-02-28)

**UI/UX Enhancements:**
- Enhanced error message visual feedback with shake animation
- Added success/error icons (✓/✖) to messages
- Implemented submit button loading states with spinner
- Extended error message display from 5s to 8s
- Added smooth fade-in/fade-out transitions
- Prevented double-submission through button disabling
- Improved message styling with shadows and thicker borders

**Feature Updates:**
- Allow removing all supplement items in intake form (supplements now optional)
- Added event listener for initial supplement remove button

**Technical Changes:**
- New utility functions: `setButtonLoading()`, `resetButton()`
- Enhanced `showMessage()` with animation triggers and variable timeouts
- Updated all form handlers with loading state management
- CSS animations: shake (errors), spinner (buttons), fade transitions
- Production bundle rebuilt with enhanced functionality

**Files Modified:**
- `static/css/styles.css` - Added animations and enhanced message styles
- `static/js/utils.js` - Enhanced message display and button state functions
- `static/js/forms.js` - Added loading states to all form handlers
- `static/js/dynamic-items.js` - Allow removing all supplement items
- `static/index.html.dev` - Show initial supplement remove button
- `static/index.html` - Production HTML regenerated
- `static/js/release/app.min.js` - Production bundle (38.89 KB)

---

# References

- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Chart.js**: https://www.chartjs.org/docs/
- **Chart.js Annotation Plugin**: https://www.chartjs.org/chartjs-plugin-annotation/
- **Python contextlib**: https://docs.python.org/3/library/contextlib.html
- **mTLS Guide**: See `CLIENT.md` for client setup instructions
