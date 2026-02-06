# Tech stack

    1. Database: sqlite3
    2. Web server: Python3 3.12 built-in http.server
    3. Frontend: HTML, CSS, JavaScript (Vanilla)

# Table Schema

    There wil be following tables.

    1. glucose table is consit of timestamp and positive integer value of glucose level
    2. insulin table is consit of timestamp and positive float point value of insulin level
    3. intake table is consit of timestamp, id of nutrition, float point value of nutrition amount in gram, and float point value of nutrition amount in kcal
    4. supplements table is consit of timestamp, string value of supplement name, and positive float point value of supplement amount
    5. event table is consit of timestamp, string value of event name, and string value of event notes
    6. nutrition table is consist of nutrition id, string value of nutrition name, float point value of kcal, float point value of weight in gram, and calculated kcal per gram (kcal/weight)

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
        timestamp DATETIME NOT NULL,
        supplement_name TEXT NOT NULL,
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

# Form Input

    There will be following forms for data input.

    1. Glucose Input Form
        - Timestamp (datetime input)
        - Glucose Level (number input)
    2. Insulin Input Form
        - Timestamp (datetime input)
        - Insulin Level (number input)
    3. Intake Input Form
        - Timestamp (datetime input)
        - Nutrition (dropdown select from nutrition table)
        - Nutrition Amount (number input in gram)
        - Nutrition kCal (auto calculated from selected nutrition)
    4. Supplements Input Form
        - Timestamp (datetime input)
        - Supplement Name (text input)
        - Supplement Amount (number input)
    5. Event Input Form
        - Timestamp (datetime input)
        - Event Name (text input)
        - Event Notes (textarea input)
    6. Nutrition Input Form
        - Nutrition Name (text input)
        - kCal (number input)
        - Weight in gram (number input)
        - kCal per gram will be automatically calculated (kcal/weight)

# Dashboard

    The dashboard will display the following data visualizations and summaries.

    1. Glucose Level Charts
        - Line chart showing weekly time-weighted average glucose levels over time
        - Time-weighted mean is calculated using trapezoidal rule: sum of (v0 + v1) / 2 * delta_t divided by total time
        - Support adjustable time range filter (start date and end date)
        - Default time range: current year (2026-01-01 to 2026-12-31)
    2. Summary time sheet
        - Table that groups data by 12 hours after intake and shows per hour average glucose level, insulin level, and nutrition intake
        - Assumption: Food intake should occur once per 12-hour period
        - Dose Time: timestamp of insulin dosing from insulin table
        - Dosage: level/amount of insulin dosed
        - Grouped Events: events concatenated as strings within the 12-hour window
        - Support adjustable time range filter (start date and end date)
        - Default time range: current month (2026-02-01 to 2026-02-28)
        - Table columns: AM/PM, Date, Dose Time, Intake Time, Dosage, Glucose Level before intake, Glucose level after intake +1hr, Glucose level after intake +2hr, Glucose level after intake +3hr, Glucose level after intake +4hr, Glucose level after intake +5hr, Glucose level after intake +6hr, ..., Glucose level after intake +12hr, kCal Intake, Grouped Events
    6. Nutrition List
        - Table listing all nutrition items with their kcal, weight, and calculated kcal per gram values

    Create sqlite3 views to calculate the time-weighted average glucose levels and the summary time sheet.

