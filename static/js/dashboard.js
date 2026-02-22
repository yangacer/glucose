// Dashboard functionality

let glucoseChart = null;

/**
 * Get color styling for glucose level
 */
function getGlucoseColor(level) {
    if (!level || level === '-') return { background: '', color: '' };
    
    const glucose = parseFloat(level);
    
    if (glucose >= 500) {
        return { background: '#000000', color: '#FFFFFF' };
    } else if (glucose >= 400) {
        return { background: '#FF0000', color: '#FFFFFF' };
    } else if (glucose >= 300) {
        return { background: '#FF00FF', color: '#FFFFFF' };
    } else if (glucose >= 200) {
        return { background: '#FFB6FF', color: '#000000' };
    } else if (glucose > 100) {
        return { background: '#98fab2', color: '#000000' };
    } else if (glucose >= 60) {
        return { background: '#6eb882', color: '#000000' };
    } else {
        return { background: '#FFFF00', color: '#FF0000' };
    }
}

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
                datasets: [
                    {
                        label: 'Glucose (mg/dL)',
                        data: data.map(d => d.glucose_mean),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.1,
                        yAxisID: 'yAxisGlucose'
                    },
                    {
                        label: 'Insulin (units)',
                        data: data.map(d => d.insulin_mean),
                        borderColor: '#f6993f',
                        backgroundColor: 'rgba(246, 153, 63, 0.1)',
                        tension: 0.1,
                        yAxisID: 'yAxisInsulin'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    yAxisGlucose: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Glucose (mg/dL)'
                        }
                    },
                    yAxisInsulin: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Insulin (units)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
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
                
                // Create cells
                const cells = [
                    { value: row.am_pm, isGlucose: false },
                    { value: row.date, isGlucose: false },
                    { value: row.dosage || '-', isGlucose: false },
                    { value: row.glucose_levels['+0'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+1'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+2'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+3'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+4'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+5'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+6'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+7'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+8'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+9'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+10'] || '-', isGlucose: true },
                    { value: row.glucose_levels['+11'] || '-', isGlucose: true },
                    { value: row.kcal_intake.toFixed(1), isGlucose: false }
                ];
                
                cells.forEach(cell => {
                    const td = document.createElement('td');
                    td.textContent = cell.value;
                    
                    if (cell.isGlucose && cell.value !== '-') {
                        const colors = getGlucoseColor(cell.value);
                        td.style.backgroundColor = colors.background;
                        td.style.color = colors.color;
                    }
                    
                    tr.appendChild(td);
                });
                
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
