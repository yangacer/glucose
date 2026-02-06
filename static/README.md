# Static Files Structure

This directory contains the frontend files for the Glucose Monitoring Dashboard.

## Directory Structure

```
static/
├── index.html              # Main HTML file
├── css/
│   └── styles.css         # All CSS styles
└── js/
    ├── config.js          # API configuration
    ├── utils.js           # Utility functions (API calls, date handling)
    ├── tabs.js            # Tab switching and navigation
    ├── dashboard.js       # Dashboard, chart, and summary functionality
    ├── data-loader.js     # Data loading (nutrition, supplements, autofill)
    ├── dynamic-items.js   # Dynamic form item management (add/remove)
    ├── forms.js           # Form submission handlers
    ├── audit.js           # Audit/edit listing and CRUD operations
    └── main.js            # Application initialization
```

## JavaScript Modules

### config.js
- Contains API endpoint configuration
- Easy to update when server address changes

### utils.js
- `submitData()` - Generic API POST request handler
- `showMessage()` - Display success/error messages
- `getCurrentTimestamp()` - Get current time in datetime-local format
- `toDbTimestamp()` - Convert datetime-local to database format
- `initializeDateInputs()` - Set default date ranges
- `setCurrentTimestamp()` - Auto-fill timestamp fields

### tabs.js
- `initializeTabs()` - Set up tab click handlers
- `switchTab()` - Switch between tabs
- `loadTabData()` - Load data when tab is activated

### dashboard.js
- `loadDashboard()` - Load all dashboard components
- `loadGlucoseChart()` - Render glucose time-weighted mean chart
- `loadSummary()` - Load summary timesheet table
- `loadNutritionList()` - Load nutrition list on dashboard

### data-loader.js
- `loadNutritionOptions()` - Load nutrition dropdown options
- `loadSupplementOptions()` - Load supplement dropdown options
- `loadSupplementsList()` - Load supplements master table
- `autofillPreviousIntake()` - Auto-fill intake form from previous window
- Helper functions for populating selects and previous data

### dynamic-items.js
- `addNutritionItem()` - Add nutrition item to intake form
- `addSupplementItem()` - Add supplement item to intake form
- `updateNutritionRemoveButtons()` - Show/hide remove buttons
- `updateSupplementRemoveButtons()` - Show/hide remove buttons
- `renumberNutritionItems()` - Renumber items after removal
- `renumberSupplementItems()` - Renumber items after removal

### forms.js
- `initializeForms()` - Set up all form submit handlers
- `handleIntakeSubmit()` - Handle intake form submission
- `resetIntakeForm()` - Reset intake form to initial state
- Form handlers for: glucose, insulin, supplements, events, nutrition

### audit.js
- Audit/edit listing functions for all entities:
  - `loadGlucoseAudit()`, `editGlucose()`, `deleteGlucose()`
  - `loadInsulinAudit()`, `editInsulin()`, `deleteInsulin()`
  - `loadIntakeAudit()`, `deleteIntake()`
  - `loadSupplementIntakeAudit()`, `deleteSupplementIntake()`
  - `loadEventAudit()`, `deleteEvent()`
  - `loadNutritionAudit()`, `deleteNutritionItem()`
  - `editSupplementRow()`, `saveSupplementRow()`, `deleteSupplement()`

### main.js
- `initializeApp()` - Initialize all modules and load initial data
- Entry point that runs on DOMContentLoaded

## CSS Organization

### styles.css
- Global styles and reset
- Component-specific styles:
  - Container and header
  - Tab navigation
  - Forms and inputs
  - Tables and data display
  - Chart and dashboard
  - Buttons and actions
  - Messages and notifications

## Load Order

The JavaScript files must be loaded in this order (dependencies):
1. config.js (no dependencies)
2. utils.js (depends on config.js)
3. tabs.js (depends on utils.js)
4. dashboard.js (depends on config.js, utils.js)
5. data-loader.js (depends on config.js, dynamic-items.js)
6. dynamic-items.js (depends on data-loader.js for circular dependency)
7. forms.js (depends on utils.js, data-loader.js)
8. audit.js (depends on config.js, utils.js, data-loader.js)
9. main.js (depends on all modules)

## Maintenance Guidelines

1. **Adding New Features**: Create new functions in the appropriate module
2. **API Changes**: Update only config.js for endpoint changes
3. **Styling Changes**: All CSS modifications go in css/styles.css
4. **New Data Types**: Add loading functions to data-loader.js
5. **New Forms**: Add handlers to forms.js
6. **New Audit Views**: Add functions to audit.js

## Testing

To test after changes:
1. Ensure server is running: `python3 server.py`
2. Open browser to http://localhost:8000
3. Test each tab and functionality
4. Check browser console for JavaScript errors
