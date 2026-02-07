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