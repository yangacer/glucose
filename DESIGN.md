# Glucose Monitoring Dashboard - Design Specification

## Overview

A personal health monitoring application for tracking glucose levels, insulin doses, nutrition intake, and related health metrics.

**Target Users:** Individuals managing diabetes or monitoring blood glucose levels

---

## Tech Stack

- **Database**: SQLite3
- **Web Server**: Python 3.12 built-in http.server
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Charts**: Chart.js with annotation plugin

---

# Data Model

## Core Entities

### Glucose Measurements
- Timestamp of measurement
- Glucose level in mg/dL

### Insulin Doses
- Timestamp of administration
- Dosage amount

### Nutrition Items (Master List)
- Nutrition name
- Total kCal value
- Weight in grams
- Auto-calculated kCal per gram

### Nutrition Intake
- Timestamp of consumption
- Reference to nutrition item
- Amount consumed in grams
- Calculated kCal for this intake

### Supplements (Master List)
- Supplement name
- Default dosage amount

### Supplement Intake
- Timestamp when taken
- Reference to supplement
- Amount taken

### Events
- Timestamp when occurred
- Event name
- Optional notes

---

# User Interface

## Navigation

Tabbed interface with the following sections:
- Dashboard (default view)
- Glucose input
- Insulin input
- Intake input
- Supplements master
- Event input
- Nutrition master

---

## Input Forms

### Glucose Input

**Purpose:** Record blood glucose measurements

**Fields:**
- Timestamp (auto-filled with current time, with "Reset to Now" button)
- Glucose Level (mg/dL)

**Features:**
- Shows last 24 hours of records
- Edit and delete existing records
- Date range filter

---

### Insulin Input

**Purpose:** Record insulin doses

**Fields:**
- Timestamp (auto-filled with current time, with "Reset to Now" button)
- Insulin Level (units)

**Features:**
- Shows last 24 hours of records
- Edit and delete existing records
- Date range filter

---

### Intake Input

**Purpose:** Record food and supplement consumption

**Fields:**
- Timestamp (shared by all items, auto-filled with current time)
- Multiple nutrition items:
  - Select nutrition from master list
  - Amount in grams
  - Auto-calculated kCal
- Multiple supplement items:
  - Select supplement from master list
  - Amount (auto-filled with default)

**Features:**
- Dynamic add/remove for nutrition and supplement items
- Auto-fill from previous time window (12-hour periods)
- Separate audit lists for nutrition and supplements
- Edit and delete existing records
- Date range filter

**Time Windows:**
- AM: 00:00-12:00
- PM: 12:00-24:00

---

### Supplements Master

**Purpose:** Maintain list of supplements

**Fields:**
- Supplement name
- Default amount (default: 1)

**Features:**
- View all supplement definitions
- Edit and delete supplements

---

### Event Input

**Purpose:** Record health-related events or notes

**Fields:**
- Timestamp (auto-filled with current time, with "Reset to Now" button)
- Event name
- Event notes (optional)

**Features:**
- Shows last 24 hours of records
- Edit and delete existing records
- Date range filter

---

### Nutrition Master

**Purpose:** Maintain list of food items

**Fields:**
- Nutrition name
- kCal
- Weight in grams
- kCal per gram (auto-calculated display)

**Features:**
- View all nutrition definitions
- Edit and delete nutrition items

---

## Dashboard

### Glucose & Insulin Level Chart

**Purpose:** Visualize trends over time

**Display:**
- Dual-axis line chart
- Left axis: Glucose levels (mg/dL) - blue line
- Right axis: Insulin levels (units) - orange line
- X-axis: Time (grouped by ISO week)

**Metrics:**
- Time-weighted average for both glucose and insulin
- Calculated using trapezoidal rule integration

**Features:**
- Adjustable date range (defaults to current year)
- Color-coded series with legend
- Responsive design

---

### CV Charts (Coefficient of Variation)

**Purpose:** Measure glucose variability

**Definition:**
```
CV = (Standard Deviation / Time-Weighted Mean) × 100
```

**Three Chart Types:**

**Last 7 Days per 12-hour**
- Day window: 05:00-16:59
- Night window: 17:00-04:59
- 14 data points (7 days × 2 windows)

**Last 30 Days per 48-hour**
- 48-hour rolling windows
- ~15 data points

**Last 30 Days per 5-day**
- 5-day (120-hour) rolling windows
- ~6 data points

**Threshold Bands:**
- Green (0-20%): Good glucose control
- Yellow (20-30%): Moderate variability
- Red (>30%): High variability, needs attention

**Features:**
- All windows anchored at 5:00 AM
- Adjustable end date (defaults to today)
- Single button updates all three charts
- Labels hidden on X-axis but available in tooltips

---

### Risk Metrics Charts

**Purpose:** Quantify hypoglycemia and hyperglycemia risk using clinical metrics

**Three Metric Types:**

**LBGI (Low Blood Glucose Index)**
- Measures hypoglycemia risk
- Threshold bands:
  - Green (0-2.5): Low risk
  - Yellow (2.5-5): Moderate risk
  - Red (>5): High risk

**HBGI (High Blood Glucose Index)**
- Measures hyperglycemia risk
- Threshold bands:
  - Green (0-4.5): Low risk
  - Yellow (4.5-9): Moderate risk
  - Red (>9): High risk

**ADRR (Average Daily Risk Range)**
- Combines LBGI and HBGI for overall risk assessment
- Groups data by calendar days
- Threshold bands:
  - Green (0-20): Low risk
  - Yellow (20-40): Moderate risk
  - Red (>40): High risk

**Chart Organization:**
- Each metric has three time window charts (7d/12h, 30d/48h, 30d/5d)
- Total of 9 charts (3 metrics × 3 windows)
- Consistent with CV chart time windows

**Features:**
- Adjustable end date (defaults to today)
- Single button updates all nine charts
- Same visual style as CV charts

---

### Summary Timesheet

**Purpose:** Daily view of glucose patterns, insulin doses, and nutrition intake

**Display:**
- Table with rows representing 12-hour time windows
- Windows: ☀️ Day (05:00-16:59) and 🌙 Night (17:00-04:59)

**Columns:**
- Window indicator (☀️ or 🌙)
- Date
- Insulin dosage (sum for window)
- Glucose levels at hourly intervals (+0 through +11)
- Total kCal intake

**Glucose Color Coding:**

| Range (mg/dL) | Background | Text |
|---------------|------------|------|
| ≥ 500 | Black | White |
| 400-499 | Red | White |
| 300-399 | Magenta | White |
| 200-299 | Light Magenta | Black |
| 101-199 | Light Green (#98fab2) | Black |
| 60-100 | Green (#6eb882) | Black |
| < 60 | Yellow | Red |

**Detail Overlay:**

Click any row to view:
- Dose time (HH:MM)
- Intake time (HH:MM)
- Nutrition items with kCal
- Supplements with amounts
- Events

Click outside overlay to dismiss.

**Features:**
- Adjustable date range (defaults to current month)
- Quick visual identification of glucose patterns
- Consolidated view of related data

---

### Nutrition List

**Purpose:** Reference table of all nutrition items

**Display:**
- Table with all nutrition master records

**Columns:**
- Nutrition name
- kCal
- Weight (grams)
- kCal per gram (calculated)

---

## Security

### Mutual TLS (mTLS)

**Purpose:** Secure authenticated connections between clients and server

**Features:**
- Server certificate verification
- Client certificate requirement
- Certificate Authority (CA) for trust chain
- TLS 1.2+ minimum version

**Certificates Required:**
- CA certificate
- Server certificate and private key
- Client certificate(s) and private key(s)

**Development Mode:**
- Can disable mTLS via environment variable
- Useful for local testing

**Certificate Generation:**
- Automated script for self-signed certificates
- Separate certificates per client
- PKCS#12 format for browser import

**Client Setup:**
- Documentation provided for:
  - Browser configuration (Chrome, Firefox, Safari, Edge)
  - OS certificate stores (Windows, macOS, Linux)
  - Mobile devices (iOS, Android)
  - Command-line tools (curl, wget)
  - Programming libraries (Python requests, Node.js)

---

## Design Principles

### Data Entry
- Minimize manual input through auto-fill and dropdowns
- Default to current time for all timestamps
- Quick "Reset to Now" buttons
- Remember previous entries for faster input

### Visualizations
- Consistent color scheme across charts
- Blue primary for glucose/CV (#667eea)
- Orange for insulin (#f6993f)
- Color-coded threshold bands (green/yellow/red)
- Bands rendered behind data for clarity
- Hidden X-axis labels to reduce clutter
- Tooltips show full information on hover

### Data Quality
- Require minimum data points for calculations
- Handle edge cases gracefully
- Display null/missing data appropriately
- Clear visual indicators for insufficient data

### Responsiveness
- All charts and tables adapt to screen size
- Mobile-friendly input forms
- Touch-friendly controls

### Audit Trail
- All forms show recent entries
- Edit and delete capabilities
- Date range filtering for historical review
- Confirmation before deletion

---

## Assumptions

### Time Windows
- Food intake occurs once per 12-hour period
- Insulin typically administered before meals
- Glucose checked at regular intervals

### Data Relationships
- Multiple nutrition items can share same timestamp
- Multiple supplements can share same timestamp
- Glucose readings are discrete measurements
- Insulin doses are discrete events

### Calculations
- Time-weighted averages account for irregular sampling
- CV and risk metrics require minimum 2 data points per window
- ISO week numbering for weekly aggregations
- 5:00 AM anchor point for daily boundaries

---

## Future Enhancements

Potential features for consideration:
- Data export (CSV, PDF reports)
- Medication tracking beyond insulin
- Blood pressure monitoring
- Weight tracking
- Exercise logging
- A1C correlation analysis
- Predictive alerts for hypo/hyperglycemia
- Multi-user support with role-based access
- Mobile app with offline sync
- Integration with CGM devices
- Meal planning and recommendations
