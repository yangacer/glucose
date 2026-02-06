// Dashboard functionality

let glucoseChart = null;

/**
 * Load all dashboard components
 */
async function loadDashboard() {
    loadGlucoseChart();
    loadSummary();
    loadNutritionList();
}

/**
 * Load and render glucose chart
 */
async function loadGlucoseChart() {
    const startDate = document.getElementById('chart-start-date').value;
    const endDate = document.getElementById('chart-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/glucose-chart?start_date=${startDate}&end_date=${endDate}`);
        const data = await response.json();
        
        const ctx = document.getElementById('glucoseChart').getContext('2d');
        
        if (glucoseChart) {
            glucoseChart.destroy();
        }
        
        glucoseChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.week),
                datasets: [{
                    label: 'Time-Weighted Mean Glucose (mg/dL)',
                    data: data.map(d => d.mean),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    } catch (err) {
        console.error('Failed to load glucose chart:', err);
    }
}

/**
 * Load and render summary timesheet
 */
async function loadSummary() {
    const startDate = document.getElementById('summary-start-date').value;
    const endDate = document.getElementById('summary-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/summary?start_date=${startDate}&end_date=${endDate}`);
        const data = await response.json();
        
        const tbody = document.getElementById('summaryBody');
        tbody.innerHTML = '';
        
        data.forEach(row => {
            if (row) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.am_pm}</td>
                    <td>${row.date}</td>
                    <td>${row.dosage || '-'}</td>
                    <td>${row.glucose_levels.before || '-'}</td>
                    <td>${row.glucose_levels['+1hr'] || '-'}</td>
                    <td>${row.glucose_levels['+2hr'] || '-'}</td>
                    <td>${row.glucose_levels['+3hr'] || '-'}</td>
                    <td>${row.glucose_levels['+4hr'] || '-'}</td>
                    <td>${row.glucose_levels['+5hr'] || '-'}</td>
                    <td>${row.glucose_levels['+6hr'] || '-'}</td>
                    <td>${row.glucose_levels['+7hr'] || '-'}</td>
                    <td>${row.glucose_levels['+8hr'] || '-'}</td>
                    <td>${row.glucose_levels['+9hr'] || '-'}</td>
                    <td>${row.glucose_levels['+10hr'] || '-'}</td>
                    <td>${row.glucose_levels['+11hr'] || '-'}</td>
                    <td>${row.glucose_levels['+12hr'] || '-'}</td>
                    <td>${row.kcal_intake.toFixed(1)}</td>
                `;
                
                // Add click handler to show overlay
                tr.addEventListener('click', () => showSummaryOverlay(row));
                
                tbody.appendChild(tr);
            }
        });
    } catch (err) {
        console.error('Failed to load summary:', err);
    }
}

/**
 * Show overlay with detailed information
 */
function showSummaryOverlay(row) {
    // Extract time from timestamp (HH:MM format)
    const formatTime = (timestamp) => {
        if (!timestamp || timestamp === '-') return '-';
        const date = new Date(timestamp);
        return date.toTimeString().slice(0, 5); // HH:MM
    };
    
    document.getElementById('overlay-dose-time').textContent = formatTime(row.dose_time);
    document.getElementById('overlay-intake-time').textContent = formatTime(row.intake_time);
    document.getElementById('overlay-nutritions').textContent = row.nutrition || '-';
    document.getElementById('overlay-supplements').textContent = row.grouped_supplements || '-';
    document.getElementById('overlay-events').textContent = row.grouped_events || '-';
    
    const overlay = document.getElementById('summaryOverlay');
    overlay.style.display = 'flex';
}

/**
 * Hide overlay
 */
function hideSummaryOverlay() {
    const overlay = document.getElementById('summaryOverlay');
    overlay.style.display = 'none';
}

// Setup overlay click handler
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('summaryOverlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            // Close overlay when clicking outside the content
            if (e.target === overlay) {
                hideSummaryOverlay();
            }
        });
    }
});

/**
 * Load nutrition list table
 */
async function loadNutritionList() {
    try {
        const response = await fetch(`${API_BASE}/nutrition`);
        const data = await response.json();
        
        const tbody = document.getElementById('nutritionListBody');
        tbody.innerHTML = '';
        
        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.id}</td>
                <td>${item.nutrition_name}</td>
                <td>${item.kcal}</td>
                <td>${item.weight}</td>
                <td>${item.kcal_per_gram.toFixed(4)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load nutrition list:', err);
    }
}
