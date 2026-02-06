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
                    <td>${row.dose_time || '-'}</td>
                    <td>${row.intake_time || '-'}</td>
                    <td>${row.dosage || '-'}</td>
                    <td>${row.nutrition || '-'}</td>
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
                    <td>${row.grouped_supplements || '-'}</td>
                    <td>${row.grouped_events || '-'}</td>
                `;
                tbody.appendChild(tr);
            }
        });
    } catch (err) {
        console.error('Failed to load summary:', err);
    }
}

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
