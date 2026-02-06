# Tech stack

    1. Database: sqlite3
    2. Web server: Python3 3.12 built-in http.server
    3. Frontend: HTML, CSS, JavaScript (Vanilla)

# Table Schema

    There will be following tables.

    1. glucose table is consist of timestamp and positive integer value of glucose level
    2. insulin table is consist of timestamp and positive float point value of insulin level
    3. intake table is consist of timestamp, id of nutrition, float point value of nutrition amount in gram, and float point value of nutrition amount in kcal
    4. supplements table is consist of timestamp, string value of supplement name, and positive float point value of supplement amount
    5. event table is consist of timestamp, string value of event name, and string value of event notes
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
        - Dynamic list of nutrition items with Add/Remove buttons
        - Multiple intake records can share the same timestamp to represent a single meal
        - For each nutrition item:
            - Nutrition (dropdown select from nutrition table)
            - Nutrition Amount (number input in gram)
            - Nutrition kCal (auto calculated from selected nutrition)
            - Remove button (to remove this nutrition item from the form)
        - The form should keep at least one nutrition item input row by default
        - The form data should be autofilled nutrition items with last
          submitted values for convenience. When the form is loaded, it should
          query recent intake records for the previous time-window and
          pre-populate the nutrition item rows with the same nutrition items
          and their amounts. If there are no previous intake records, it should
          show one empty nutrition item row by default.
        - Time-window definition: previous_time_window(current_time_window(current_time))
          where current_time_window returns AM (00:00-12:00) or PM (12:00-24:00) based on current time,
          and previous_time_window returns the immediately preceding 12-hour window
          (e.g., if current time is 8:46 AM, current window is AM, previous window is yesterday's PM)
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

    Below each form there should be a listing for auditing and editing existing data.
    Each listing show entries for last 24 hours and have option to filter by date range.

# Dashboard

    The dashboard will display the following data visualizations and summaries.

    1. Glucose Level Charts
        - Line chart showing weekly time-weighted average glucose levels over time
        - Time-weighted mean is calculated using trapezoidal rule: sum of (v0 + v1) / 2 * delta_t divided by total time
        - Support adjustable time range filter (start date and end date)
        - Default time range: current year (dynamically calculated based on current date)
    2. Summary time sheet
        - Table that groups data by non-overlapping 12-hour time windows and shows per hour average glucose level and nutrition intake
        - Time windows are fixed: 00:00-12:00 (AM) and 12:00-24:00 (PM) for each day
        - Each row represents one 12-hour window
        - Assumption: Food intake should occur once per 12-hour period and the intake could be mix of multiple nutrition items with same or similar timestamps
        - Dose Time: timestamp of the most recent insulin dosing from insulin table within the same 12-hour window
        - Dosage: level/amount of the most recent insulin dosed within the same 12-hour window
        - Grouped Events: events concatenated as strings within the 12-hour window
        - Support adjustable time range filter (start date and end date)
        - Default time range: current month (dynamically calculated based on current date)
        - Table columns: AM/PM, Date, Dose Time, First Intake Time, Dosage,
          Nutrition, Glucose Level before intake, Glucose level after intake
          +1hr, Glucose level after intake +2hr, Glucose level after intake +3hr,
          Glucose level after intake +4hr, Glucose level after intake +5hr,
          Glucose level after intake +6hr, ..., Glucose level after intake +12hr,
          kCal Intake, Grouped Supplements, Grouped Events
        - First Intake Time: timestamp of the first (earliest) intake record in the 12-hour window
        - For the Nutrition column: group all nutrition intake records within the 12-hour window, 
          and list the individual nutrition items as a concatenated string (e.g., "Apple (95 kcal), Bread (80 kcal)")
        - For the kCal Intake column: sum all kcal values from nutrition intake records within the 12-hour window
          to show the total caloric intake for that period
        - For the Grouped Supplements column: concatenate all supplement entries within the 
          12-hour window showing name and amount (e.g., "Vitamin C 500, Magnesium 200")

    6. Nutrition List
        - Table listing all nutrition items with their kcal, weight, and calculated kcal per gram values

