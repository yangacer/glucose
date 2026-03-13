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

    // Dashboard update buttons
    document.getElementById('update-glucose-chart-btn').addEventListener('click', loadGlucoseChart);
    document.getElementById('update-cv-btn').addEventListener('click', loadCVCharts);
    document.getElementById('update-risk-btn').addEventListener('click', loadRiskMetrics);
    document.getElementById('update-summary-btn').addEventListener('click', loadSummary);

    // Reset-to-now buttons
    document.getElementById('reset-glucose-ts-btn').addEventListener('click', () => resetToNow('glucose-timestamp'));
    document.getElementById('reset-insulin-ts-btn').addEventListener('click', () => resetToNow('insulin-timestamp'));
    document.getElementById('reset-intake-ts-btn').addEventListener('click', () => resetToNow('intake-timestamp'));
    document.getElementById('reset-event-ts-btn').addEventListener('click', () => resetToNow('event-timestamp'));

    // Audit filter buttons
    document.getElementById('filter-glucose-btn').addEventListener('click', loadGlucoseAudit);
    document.getElementById('filter-insulin-btn').addEventListener('click', loadInsulinAudit);
    document.getElementById('filter-intake-btn').addEventListener('click', loadIntakeAudit);
    document.getElementById('filter-supplement-intake-btn').addEventListener('click', loadSupplementIntakeAudit);
    document.getElementById('filter-event-btn').addEventListener('click', loadEventAudit);

    // Load initial data
    loadDashboard();
    setCurrentTimestamp();
}

// Run when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);
