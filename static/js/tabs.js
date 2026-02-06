// Tab management

/**
 * Initialize tab switching functionality
 */
function initializeTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });
}

/**
 * Switch to specified tab
 * @param {string} targetTab - Tab ID to switch to
 */
function switchTab(targetTab) {
    // Update button states
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    document.querySelector(`[data-tab="${targetTab}"]`).classList.add('active');
    document.getElementById(targetTab).classList.add('active');
    
    // Load tab-specific data
    loadTabData(targetTab);
    
    // Auto-fill timestamps after switching
    setTimeout(setCurrentTimestamp, 100);
}

/**
 * Load data when tab is activated
 * @param {string} tab - Tab ID
 */
function loadTabData(tab) {
    switch(tab) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'intake':
            loadNutritionOptions();
            loadSupplementOptions();
            loadIntakeAudit();
            loadSupplementIntakeAudit();
            autofillPreviousIntake();
            break;
        case 'supplements':
            loadSupplementsList();
            break;
        case 'nutrition':
            loadNutritionList();
            loadNutritionAudit();
            break;
        case 'event':
            loadEventAudit();
            break;
        case 'glucose':
            loadGlucoseAudit();
            break;
        case 'insulin':
            loadInsulinAudit();
            break;
    }
}
