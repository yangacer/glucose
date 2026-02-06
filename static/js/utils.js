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
 * Show message to user
 * @param {string} elementId - ID of message element
 * @param {boolean} success - Whether operation was successful
 * @param {string} message - Message to display
 */
function showMessage(elementId, success, message) {
    const msgEl = document.getElementById(elementId);
    msgEl.textContent = message;
    msgEl.className = 'message ' + (success ? 'success' : 'error');
    setTimeout(() => {
        msgEl.textContent = '';
        msgEl.className = 'message';
    }, 5000);
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
    return datetimeLocal.replace('T', ' ') + ':00';
}

/**
 * Initialize default date range inputs
 */
function initializeDateInputs() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    
    // Chart dates - current year
    document.getElementById('chart-start-date').value = `${year}-01-01`;
    document.getElementById('chart-end-date').value = `${year}-12-31`;
    
    // Summary dates - current month
    const lastDay = new Date(year, now.getMonth() + 1, 0).getDate();
    document.getElementById('summary-start-date').value = `${year}-${month}-01`;
    document.getElementById('summary-end-date').value = `${year}-${month}-${lastDay}`;
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
