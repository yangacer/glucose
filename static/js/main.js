// Main initialization

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize modules
    initializeTabs();
    initializeForms();
    initializeDynamicItems();
    initializeDateInputs();
    
    // Load initial data
    loadDashboard();
    setCurrentTimestamp();
}

// Run when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);
