// Utility functions

/**
 * Submit data to API endpoint
 * @param {string} endpoint - API endpoint path
 * @param {object} data - Data to submit
 * @returns {Promise<{success: boolean, message: string}>}
 */
async function submitData(endpoint, data) {
    try {
        const response = await fetch(API_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            return { success: true, message: 'Data submitted successfully!' };
        } else {
            const error = await response.json();
            return { success: false, message: error.error || 'Submission failed' };
        }
    } catch (err) {
        return { success: false, message: 'Network error: ' + err.message };
    }
}

/**
 * Show message to user with improved visual feedback
 * @param {string} elementId - ID of message element
 * @param {boolean} success - Whether operation was successful
 * @param {string} message - Message to display
 */
function showMessage(elementId, success, message) {
    const msgEl = document.getElementById(elementId);
    
    // Clear previous classes and content
    msgEl.className = 'message';
    msgEl.textContent = message;
    
    // Add success or error class
    msgEl.classList.add(success ? 'success' : 'error');
    
    // Trigger animation
    setTimeout(() => msgEl.classList.add('show'), 10);
    
    // Clear message after timeout (longer for errors)
    const timeout = success ? 5000 : 8000;
    setTimeout(() => {
        msgEl.classList.remove('show');
        setTimeout(() => {
            msgEl.textContent = '';
            msgEl.className = 'message';
        }, 300);
    }, timeout);
}

/**
 * Get current timestamp in datetime-local format
 * @returns {string} Formatted timestamp
 */
function getCurrentTimestamp() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Convert datetime-local format to database timestamp
 * @param {string} datetimeLocal - Datetime local value
 * @returns {string} Database timestamp format
 */
function toDbTimestamp(datetimeLocal) {
    return new Date(datetimeLocal).toISOString().replace('T', ' ').slice(0, 19);
}

/**
 * Initialize default date range inputs
 */
function initializeDateInputs() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    
    // Chart dates - current year
    document.getElementById('chart-start-date').value = `${year}-01-01`;
    document.getElementById('chart-end-date').value = `${year}-12-31`;
    
    // Summary dates - current month
    const lastDay = new Date(year, now.getMonth() + 1, 0).getDate();
    document.getElementById('summary-start-date').value = `${year}-${month}-01`;
    document.getElementById('summary-end-date').value = `${year}-${month}-${lastDay}`;
    
    // CV charts date - today
    document.getElementById('cv-end-date').value = `${year}-${month}-${day}`;
    
    // Risk metrics date - today
    document.getElementById('risk-end-date').value = `${year}-${month}-${day}`;
}

/**
 * Auto-fill current timestamp for all datetime inputs
 */
function setCurrentTimestamp() {
    const datetimeLocal = getCurrentTimestamp();
    
    document.querySelectorAll('input[type="datetime-local"]').forEach(input => {
        if (!input.value) {
            input.value = datetimeLocal;
        }
    });
}

/**
 * Reset timestamp input to current time
 * @param {string} inputId - ID of the datetime-local input element
 */
function resetToNow(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        const timestamp = getCurrentTimestamp();
        input.value = timestamp;
    }
}

/**
 * Set button to loading state
 * @param {HTMLButtonElement} button - Button element
 * @param {string} loadingText - Optional loading text
 */
function setButtonLoading(button, loadingText = 'Submitting...') {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
    button.classList.add('submitting');
}

/**
 * Reset button from loading state
 * @param {HTMLButtonElement} button - Button element
 */
function resetButton(button) {
    if (button.dataset.originalText) {
        button.textContent = button.dataset.originalText;
        delete button.dataset.originalText;
    }
    button.disabled = false;
    button.classList.remove('submitting');
}

/**
 * Parse a UTC database timestamp string into a Date object.
 * All timestamps stored in the DB are UTC (no 'Z' suffix by convention).
 * @param {string} ts - UTC timestamp (YYYY-MM-DD HH:MM:SS)
 * @returns {Date}
 */
function utcDbToDate(ts) {
    return new Date(ts.replace(' ', 'T') + 'Z');
}

/**
 * Convert database timestamp to datetime-local format
 * @param {string} dbTimestamp - Database timestamp (YYYY-MM-DD HH:MM:SS)
 * @returns {string} Datetime local format (YYYY-MM-DDTHH:MM)
 */
function toInputTimestamp(dbTimestamp) {
    const d = utcDbToDate(dbTimestamp);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Format a UTC database timestamp for display in the browser's local time
 * @param {string} utcStr - UTC timestamp (YYYY-MM-DD HH:MM:SS)
 * @returns {string} Localised display string
 */
function formatTimestamp(utcStr) {
    return utcDbToDate(utcStr).toLocaleString();
}

/**
 * Return the browser's IANA timezone name
 * @returns {string} e.g. "Asia/Taipei"
 */
function getClientTz() {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
