# Tech Stack

1. **Database**: SQLite3
2. **Web Server**: Python 3.12 built-in http.server
3. **Frontend**: HTML, CSS, JavaScript (Vanilla)

# Database Schema

## Tables Overview

1. **glucose**: Records glucose level measurements
2. **insulin**: Records insulin dosing information
3. **intake**: Records nutrition intake transactions
4. **supplements**: Master table of predefined supplements
5. **supplement_intake**: Records supplement intake transactions
6. **event**: Records events and notes
7. **nutrition**: Master table of predefined nutrition items

## Table Definitions

### 1. glucose
- `timestamp` (DATETIME): When the glucose level was measured
- `level` (INTEGER): Glucose level value

### 2. insulin
- `timestamp` (DATETIME): When insulin was administered
- `level` (REAL): Insulin dosage amount

### 3. intake
- `timestamp` (DATETIME): When food was consumed
- `nutrition_id` (INTEGER): Reference to nutrition table
- `nutrition_amount` (REAL): Amount in grams
- `nutrition_kcal` (REAL): Calculated kcal value

### 4. supplements
- `supplement_name` (TEXT): Name of the supplement
- `default_amount` (REAL): Default dosage amount (default: 1)

### 5. supplement_intake
- `timestamp` (DATETIME): When supplement was taken
- `supplement_id` (INTEGER): Reference to supplements table
- `supplement_amount` (REAL): Amount taken

### 6. event
- `timestamp` (DATETIME): When the event occurred
- `event_name` (TEXT): Name of the event
- `event_notes` (TEXT): Optional notes

### 7. nutrition
- `nutrition_name` (TEXT): Name of the nutrition item
- `kcal` (REAL): Total kcal value
- `weight` (REAL): Weight in grams
- `kcal_per_gram` (REAL): Auto-calculated (kcal / weight)

## SQL Schema

```sql
CREATE TABLE glucose (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    level INTEGER NOT NULL
);

CREATE TABLE insulin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    level REAL NOT NULL
);

CREATE TABLE intake (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nutrition_id INTEGER REFERENCES nutrition(id),
    timestamp DATETIME NOT NULL,
    nutrition_amount REAL NOT NULL,
    nutrition_kcal REAL NOT NULL
);

CREATE TABLE supplements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplement_name TEXT NOT NULL,
    default_amount REAL NOT NULL DEFAULT 1
);

CREATE TABLE supplement_intake (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    supplement_id INTEGER REFERENCES supplements(id),
    supplement_amount REAL NOT NULL
);

CREATE TABLE event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    event_name TEXT NOT NULL,
    event_notes TEXT
);

CREATE TABLE nutrition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nutrition_name TEXT NOT NULL,
    kcal REAL NOT NULL,
    weight REAL NOT NULL,
    kcal_per_gram REAL GENERATED ALWAYS AS (kcal / weight) STORED
);
```

# User Interface

## Form Inputs

All forms include timestamp autofill functionality and audit/edit listings showing recent entries.

### 1. Glucose Input Form
**Fields:**
- Timestamp (datetime-local input, autofilled with current time)
- Glucose Level (number input)

**Audit & Edit:** Shows last 24 hours of glucose records with date range filter

---

### 2. Insulin Input Form
**Fields:**
- Timestamp (datetime-local input, autofilled with current time)
- Insulin Level (number input)

**Audit & Edit:** Shows last 24 hours of insulin records with date range filter

---

### 3. Intake Input Form
This form supports multiple nutrition and supplement items sharing the same timestamp.

**Fields:**
- **Timestamp** (datetime-local input, autofilled with current time) - shared by all items

**Nutrition Items Section:**
- Dynamic list with Add/Remove buttons (minimum 1 item)
- For each nutrition item:
  - Nutrition dropdown (select from nutrition master table)
  - Amount in grams (number input)
  - kCal (auto-calculated from selected nutrition)
  - Remove button

**Supplement Items Section:**
- Dynamic list with Add/Remove buttons (minimum 1 item)
- For each supplement item:
  - Supplement dropdown (select from supplements master table)
  - Amount (number input, autofilled with default_amount)
  - Remove button

**Autofill Behavior:**
- Queries records from the previous time-window
- Pre-populates nutrition items with same items and amounts
- Pre-populates supplement items with same items and amounts
- Time-window definition: `previous_time_window(current_time_window(current_time))`
  - Current window: AM (00:00-12:00) or PM (12:00-24:00)
  - Previous window: immediately preceding 12-hour window
  - Example: if current time is 8:46 AM, previous window is yesterday's PM

**Audit & Edit:** Two separate sections:
1. **"Nutrition"** listing (intake table records)
2. **"Supplements"** listing (supplement_intake table records)
- Both share the same date range filters

---

### 4. Supplements Master Form
**Fields:**
- Supplement Name (text input)
- Default Amount (number input, default value = 1)

**Audit & Edit:** Shows all supplement master records with date range filter

---

### 5. Event Input Form
**Fields:**
- Timestamp (datetime-local input, autofilled with current time)
- Event Name (text input)
- Event Notes (textarea input)

**Audit & Edit:** Shows last 24 hours of event records with date range filter

---

### 6. Nutrition Master Form
**Fields:**
- Nutrition Name (text input)
- kCal (number input)
- Weight in grams (number input)
- kCal per gram (auto-calculated and displayed as kcal/weight)

**Audit & Edit:** Shows all nutrition master records with date range filter

## Dashboard

### 1. Glucose Level Chart

**Visualization:**
- Line chart showing time-weighted average glucose levels

**Time-Weighted Mean Calculation:**
- Uses trapezoidal rule: `Σ((v0 + v1) / 2 × Δt) / total_time`
- Implements the algorithm from `time-weighted-mean.py`

**Features:**
- Adjustable time range filter (start date and end date)
- **Default range:** Current year (dynamically calculated based on current date)

---

### 2. Summary Timesheet

**Purpose:**
Groups data by 12-hour time windows showing glucose trends and intake information.

**Time Window Definition:**
- Fixed non-overlapping windows: AM (00:00-12:00) and PM (12:00-24:00)
- Each row represents one 12-hour period

**Assumptions:**
- Food intake occurs once per 12-hour period
- Intake may consist of multiple nutrition items with same/similar timestamps

**Features:**
- Adjustable time range filter (start date and end date)
- **Default range:** Current month (dynamically calculated based on current date)

**Table Columns (Visible in Main Table):**

| Column | Description |
|--------|-------------|
| **AM/PM** | Time window indicator |
| **Date** | Calendar date |
| **Dosage** | Amount of most recent insulin dose |
| **Glucose Level before intake** | Glucose reading before first intake (with color coding) |
| **Glucose level +1hr** through **+12hr** | Glucose readings at hourly intervals after first intake (with color coding) |
| **kCal Intake** | Total kcal sum for the window |

**Glucose Level Color Coding:**

All glucose level cells in the timesheet are color-coded based on the following thresholds:

| Glucose Range | Background Color | Font Color |
|---------------|-----------------|------------|
| ≥ 500 | Black (#000000) | White |
| 400 - 499 | Red (#FF0000) | White |
| 300 - 399 | Magenta (#FF00FF) | White |
| 200 - 299 | Light Magenta (#FFB6FF or similar) | Black |
| 101 - 199 | #98fab2 | Black |
| 60 - 100 | #6eb882 | Black |
| < 60 | Yellow (#FFFF00) | Red |

**Details Shown in Overlay (Not in Main Table):**

When a row is clicked, an overlay displays the following details:
- **Dose Time**: Timestamp only (HH:MM format) of most recent insulin dose in window
- **Intake Time**: Timestamp only (HH:MM format) of earliest intake in window
- **Nutritions**: Concatenated list of nutrition items with kcal (e.g., "Apple (95 kcal), Bread (80 kcal)")
- **Supplements**: Concatenated supplement entries with amounts (e.g., "Vitamin C 500, Magnesium 200")
- **Events**: Concatenated event names in the window

**Overlay Interaction:**
- Click any timesheet row to display overlay with detail information
- Overlay appears as a floating panel positioned over the page content
- Click anywhere outside the overlay to dismiss it
- Only one row can be selected at a time
- No multiple row selection supported

**Data Aggregation Rules:**
- **Dose Time & Dosage:** Query insulin table for most recent record within the same 12-hour window
- **First Intake Time:** Earliest intake timestamp in the window
- **Nutrition:** All nutrition intake records grouped and concatenated
- **kCal Intake:** Sum of all nutrition_kcal values in the window
- **Grouped Supplements:** All supplement_intake records concatenated with name and amount
- **Grouped Events:** All event records concatenated as strings

---

### 3. Nutrition List

**Display:**
Table listing all nutrition master records

**Columns:**
- Nutrition Name
- kCal
- Weight (grams)
- kCal per gram (calculated value)

---

# Security: Mutual TLS (mTLS)

## Overview

The application supports mutual TLS authentication to ensure secure, authenticated connections between clients and the server. Both server and client present certificates for verification.

## Components

### 1. Server mTLS Configuration

**Implementation in `server.py`:**
- Extends `http.server.HTTPServer` with SSL/TLS support
- Requires client certificate verification (`ssl.CERT_REQUIRED`)
- Loads server certificate and private key
- Loads CA certificate for client verification
- Enforces minimum TLS version (TLS 1.2 or higher)

**Configuration:**
- Certificate paths configurable via environment variables or config file
- Default certificate directory: `certs/`
- Required files:
  - `certs/ca/ca-cert.pem` - Certificate Authority certificate
  - `certs/server/server-cert.pem` - Server certificate
  - `certs/server/server-key.pem` - Server private key
  
**Features:**
- Logs client certificate CN (Common Name) on connection
- Supports TLS 1.2 and TLS 1.3
- Configurable cipher suites for security
- Optional development mode to disable mTLS (via environment variable `MTLS_ENABLED=false`)
- **Directory listing disabled** to prevent unauthorized browsing of server filesystem

**Security Settings:**
- `ssl.CERT_REQUIRED` - Mandatory client certificate
- Verify client certificate against CA
- Strong cipher suite selection
- Disable insecure protocols (SSLv2, SSLv3, TLS 1.0, TLS 1.1)
- Directory listing forbidden (returns 403 Forbidden)

### 2. Certificate Generation Script

**Script: `generate-certs.sh`**

**Purpose:** Generate self-signed certificates for development and testing

**Generates:**
1. **Certificate Authority (CA)**
   - CA private key (4096-bit RSA)
   - CA certificate (valid 10 years)
   - Location: `certs/ca/`

2. **Server Certificate**
   - Server private key (4096-bit RSA)
   - Certificate signing request (CSR)
   - Server certificate signed by CA (valid 2 years)
   - Subject Alternative Names (SAN) for localhost and common IPs
   - Location: `certs/server/`

3. **Client Certificate(s)**
   - Client private key (4096-bit RSA)
   - Client certificate signing request (CSR)
   - Client certificate signed by CA (valid 1 year)
   - Location: `certs/clients/`
   - Naming: `client-{name}-cert.pem` and `client-{name}-key.pem`

**Features:**
- Interactive mode: prompts for details (CN, organization, etc.)
- Non-interactive mode: uses defaults for automation
- Generates PKCS#12 format for browser import (`.p12` files)
- Sets appropriate file permissions (private keys: 600)
- Creates directory structure automatically

**Usage Examples:**
```bash
# Generate all certificates (CA, server, and one client)
./generate-certs.sh

# Generate additional client certificate
./generate-certs.sh --client-only --name "john-doe"

# Non-interactive with defaults
./generate-certs.sh --auto
```

### 3. Client Configuration Documentation

**Document: `CLIENT.md`**

**Contents:**

1. **Overview**
   - What is mTLS and why it's used
   - Prerequisites for client setup

2. **Certificate Installation**
   - Browser configuration (Chrome, Firefox, Safari, Edge)
   - Operating system certificate store (Windows, macOS, Linux)
   - Mobile devices (iOS, Android)

3. **Application-Specific Setup**
   - Python `requests` library with client certificates
   - curl command examples
   - wget configuration
   - JavaScript/Node.js fetch with certificates

4. **Testing Connection**
   - Verify certificate installation
   - Test commands for validation
   - Common error messages and solutions

5. **Troubleshooting**
   - Certificate not recognized
   - Certificate expired
   - Connection refused errors
   - Browser-specific issues
   - Certificate format conversion (PEM, PKCS#12, DER)

6. **Security Best Practices**
   - Protect private keys
   - Certificate storage recommendations
   - Expiration monitoring
   - Revocation procedures

7. **Example Code Snippets**
   - Python client example
   - curl commands for API testing
   - Browser bookmark setup

**Format:** Markdown with clear step-by-step instructions and screenshots where helpful

---

## Additional Features

### Certificate Management
- **Expiration Monitoring**: Server logs warnings for certificates expiring within 30 days
- **Multiple Client Certificates**: Support for different users with unique certificates
- **Certificate Revocation**: Future support for CRL (Certificate Revocation List)

### Logging & Audit
- Log all mTLS connections with client certificate CN
- Timestamp and IP address logging
- Failed authentication attempts logged
- Audit trail in SQLite database (optional future feature)

### Configuration File
**Optional `mtls_config.json`:**
```json
{
  "enabled": true,
  "ca_cert": "certs/ca/ca-cert.pem",
  "server_cert": "certs/server/server-cert.pem",
  "server_key": "certs/server/server-key.pem",
  "min_tls_version": "TLS1_2",
  "cipher_suites": "HIGH:!aNULL:!MD5",
  "require_client_cert": true,
  "log_client_cn": true
}
```

### Development Mode
- Environment variable `MTLS_ENABLED=false` disables mTLS for local testing
- Warning message displayed when running without mTLS
- Useful for development and debugging

---

## Implementation Notes

### Server Changes
- Wrap existing `HTTPServer` with `ssl.wrap_socket()` or `SSLContext`
- Add certificate loading and validation logic
- Maintain backward compatibility with non-SSL mode for testing
- Minimal changes to existing handler classes

### Testing
- Include test script: `test-mtls.sh` to validate configuration
- Verify certificate chain
- Test with valid and invalid certificates
- Ensure proper error handling for certificate errors

### Deployment Considerations
- Certificate files must be readable by server process
- Private keys should have restricted permissions (600)
- Consider using proper CA for production (not self-signed)
- Document certificate renewal process
- Backup CA private key securely (required for issuing new client certs)