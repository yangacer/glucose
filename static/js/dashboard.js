// Dashboard functionality

let glucoseChart = null;
let cvChart7d12h = null;
let cvChart30d48h = null;
let cvChart30d5d = null;
let lbgiChart7d12h = null;
let lbgiChart30d48h = null;
let lbgiChart30d5d = null;
let hbgiChart7d12h = null;
let hbgiChart30d48h = null;
let hbgiChart30d5d = null;
let adrrChart7d12h = null;
let adrrChart30d48h = null;
let adrrChart30d5d = null;

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
    loadCVCharts();
    loadRiskMetrics();
    loadPrediction();
}

/**
 * Load and render glucose chart
 */
async function loadGlucoseChart() {
    const startDate = document.getElementById('chart-start-date').value;
    const endDate = document.getElementById('chart-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/glucose-chart?start_date=${startDate}&end_date=${endDate}&tz=${encodeURIComponent(getClientTz())}`);
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
        const response = await fetch(`${API_BASE}/dashboard/summary?start_date=${startDate}&end_date=${endDate}&tz=${encodeURIComponent(getClientTz())}`);
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
    // Parse as UTC then display in browser local time
    const formatTime = (timestamp) => {
        if (!timestamp || timestamp === '-') return '-';
        return utcDbToDate(timestamp).toTimeString().slice(0, 5); // HH:MM local time
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

/**
 * Load and render CV charts
 */
async function loadCVCharts() {
    const endDate = document.getElementById('cv-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/cv-charts?end_date=${endDate}&tz=${encodeURIComponent(getClientTz())}`);
        const data = await response.json();
        
        renderCVChart('cvChart7d12h', data.cv_7d_12h, cvChart7d12h);
        renderCVChart('cvChart30d48h', data.cv_30d_48h, cvChart30d48h);
        renderCVChart('cvChart30d5d', data.cv_30d_5d, cvChart30d5d);
    } catch (err) {
        console.error('Failed to load CV charts:', err);
    }
}

/**
 * Render a single CV chart
 */
function renderCVChart(canvasId, data, chartInstance) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    const maxCV = Math.max(...data.map(d => d.cv || 0), 100);
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: 'CV (%)',
                data: data.map(d => d.cv),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    ticks: {
                        display: false
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: Math.max(maxCV, 40),
                    title: {
                        display: true,
                        text: 'CV (%)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                annotation: {
                    annotations: {
                        greenBand: {
                            type: 'box',
                            yMin: 0,
                            yMax: 25,
                            backgroundColor: 'rgba(0, 255, 0, 0.3)',
                            borderWidth: 0,
                            drawTime: 'beforeDatasetsDraw'
                        },
                        yellowBand: {
                            type: 'box',
                            yMin: 25,
                            yMax: 35,
                            backgroundColor: 'rgba(255, 255, 0, 0.3)',
                            borderWidth: 0,
                            drawTime: 'beforeDatasetsDraw'
                        },
                        redBand: {
                            type: 'box',
                            yMin: 35,
                            yMax: Math.max(maxCV, 45),
                            backgroundColor: 'rgba(255, 0, 0, 0.3)',
                            borderWidth: 0,
                            drawTime: 'beforeDatasetsDraw'
                        }
                    }
                }
            }
        }
    });
    
    if (canvasId === 'cvChart7d12h') {
        cvChart7d12h = chart;
    } else if (canvasId === 'cvChart30d48h') {
        cvChart30d48h = chart;
    } else if (canvasId === 'cvChart30d5d') {
        cvChart30d5d = chart;
    }
}

/**
 * Load and render CV charts
 */
async function loadCVCharts() {
    const endDate = document.getElementById('cv-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/cv-charts?end_date=${endDate}&tz=${encodeURIComponent(getClientTz())}`);
        const data = await response.json();
        
        renderCVChart('cvChart7d12h', data.cv_7d_12h, cvChart7d12h);
        renderCVChart('cvChart30d48h', data.cv_30d_48h, cvChart30d48h);
        renderCVChart('cvChart30d5d', data.cv_30d_5d, cvChart30d5d);
    } catch (err) {
        console.error('Failed to load CV charts:', err);
    }
}

/**
 * Load and render risk metrics charts
 */
async function loadRiskMetrics() {
    const endDate = document.getElementById('risk-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/risk-metrics?end_date=${endDate}&tz=${encodeURIComponent(getClientTz())}`);
        const data = await response.json();
        
        // Render LBGI charts (adjusted for cats)
        renderRiskChart('lbgiChart7d12h', data.lbgi_7d_12h, lbgiChart7d12h, 'LBGI', 
                       [3.5, 7], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        renderRiskChart('lbgiChart30d48h', data.lbgi_30d_48h, lbgiChart30d48h, 'LBGI',
                       [3.5, 7], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        renderRiskChart('lbgiChart30d5d', data.lbgi_30d_5d, lbgiChart30d5d, 'LBGI',
                       [3.5, 7], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        
        // Render HBGI charts (adjusted for cats)
        renderRiskChart('hbgiChart7d12h', data.hbgi_7d_12h, hbgiChart7d12h, 'HBGI',
                       [6, 12], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        renderRiskChart('hbgiChart30d48h', data.hbgi_30d_48h, hbgiChart30d48h, 'HBGI',
                       [6, 12], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        renderRiskChart('hbgiChart30d5d', data.hbgi_30d_5d, hbgiChart30d5d, 'HBGI',
                       [6, 12], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        
        // Render ADRR charts (adjusted for cats)
        renderRiskChart('adrrChart7d12h', data.adrr_7d_12h, adrrChart7d12h, 'ADRR',
                       [25, 50], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        renderRiskChart('adrrChart30d48h', data.adrr_30d_48h, adrrChart30d48h, 'ADRR',
                       [25, 50], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
        renderRiskChart('adrrChart30d5d', data.adrr_30d_5d, adrrChart30d5d, 'ADRR',
                       [25, 50], ['rgba(0, 255, 0, 0.3)', 'rgba(255, 255, 0, 0.3)', 'rgba(255, 0, 0, 0.3)']);
    } catch (err) {
        console.error('Failed to load risk metrics:', err);
    }
}

/**
 * Render a single risk metric chart
 */
function renderRiskChart(canvasId, data, chartInstance, metricName, thresholds, colors) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    const maxValue = Math.max(...data.map(d => d.value || 0), thresholds[1] * 1.5);
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.label),
            datasets: [{
                label: metricName,
                data: data.map(d => d.value),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.1,
                spanGaps: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    ticks: {
                        display: false
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    max: maxValue,
                    title: {
                        display: true,
                        text: metricName
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                annotation: {
                    annotations: {
                        greenBand: {
                            type: 'box',
                            yMin: 0,
                            yMax: thresholds[0],
                            backgroundColor: colors[0],
                            borderWidth: 0,
                            drawTime: 'beforeDatasetsDraw'
                        },
                        yellowBand: {
                            type: 'box',
                            yMin: thresholds[0],
                            yMax: thresholds[1],
                            backgroundColor: colors[1],
                            borderWidth: 0,
                            drawTime: 'beforeDatasetsDraw'
                        },
                        redBand: {
                            type: 'box',
                            yMin: thresholds[1],
                            yMax: maxValue,
                            backgroundColor: colors[2],
                            borderWidth: 0,
                            drawTime: 'beforeDatasetsDraw'
                        }
                    }
                }
            }
        }
    });
    
    // Update global chart instance
    if (canvasId === 'lbgiChart7d12h') {
        lbgiChart7d12h = chart;
    } else if (canvasId === 'lbgiChart30d48h') {
        lbgiChart30d48h = chart;
    } else if (canvasId === 'lbgiChart30d5d') {
        lbgiChart30d5d = chart;
    } else if (canvasId === 'hbgiChart7d12h') {
        hbgiChart7d12h = chart;
    } else if (canvasId === 'hbgiChart30d48h') {
        hbgiChart30d48h = chart;
    } else if (canvasId === 'hbgiChart30d5d') {
        hbgiChart30d5d = chart;
    } else if (canvasId === 'adrrChart7d12h') {
        adrrChart7d12h = chart;
    } else if (canvasId === 'adrrChart30d48h') {
        adrrChart30d48h = chart;
    } else if (canvasId === 'adrrChart30d5d') {
        adrrChart30d5d = chart;
    }
}

/**
 * Load and display glucose/insulin prediction
 */
async function loadPrediction() {
    const container = document.getElementById('predictionContent');
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/prediction?lookback_days=30&tz=${encodeURIComponent(getClientTz())}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch prediction');
        }
        
        const data = await response.json();
        
        if (data.error) {
            displayPredictionError(container, data);
            return;
        }
        
        displayPrediction(container, data);
    } catch (error) {
        console.error('Error loading prediction:', error);
        container.innerHTML = `
            <div class="prediction-error">
                <p><strong>Unable to load prediction</strong></p>
                <p>${error.message}</p>
            </div>
        `;
    }
}

/**
 * Display prediction data
 */
function displayPrediction(container, data) {
    const { prediction, next_window, basis, warnings } = data;
    
    if (!prediction) {
        displayPredictionError(container, data);
        return;
    }
    
    const confidenceClass = `confidence-${prediction.confidence.toLowerCase()}`;
    const confidenceDots = getConfidenceDots(prediction.confidence);
    
    let html = `
        <div class="prediction-box">
            <div class="prediction-item">
                <h3>📊 Predicted Glucose</h3>
                <div class="prediction-value">${prediction.glucose} mg/dL</div>
                <div class="prediction-range">Range: ${prediction.glucose_range[0]} - ${prediction.glucose_range[1]} mg/dL</div>
            </div>
            <div class="prediction-item">
                <h3>💉 Recommended Insulin</h3>
                <div class="prediction-value">
                    ${prediction.insulin_recommended !== null ? prediction.insulin_recommended + ' units' : 'N/A'}
                </div>
                ${prediction.insulin_recommended === null ? '<div class="prediction-range">Insufficient data</div>' : ''}
            </div>
        </div>
        
        <div class="prediction-confidence">
            <div>Time Window: <strong>${next_window}</strong></div>
            <div class="confidence-level ${confidenceClass}">
                Confidence: ${prediction.confidence}
            </div>
            <div class="confidence-dots">${confidenceDots}</div>
        </div>
        
        <div class="prediction-basis">
            Based on ${basis.data_points} glucose readings over ${basis.lookback_days} days
            ${basis.recent_cv !== null ? `(CV: ${basis.recent_cv}%)` : ''}
        </div>
    `;
    
    if (warnings && warnings.length > 0) {
        html += `
            <div class="prediction-warnings">
                <h4>⚠️ Warnings</h4>
                <ul>
                    ${warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    html += `
        <div class="prediction-disclaimer">
            This prediction is for informational purposes only. Always verify with actual glucose readings and consult your veterinarian for dosing decisions.
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Display prediction error
 */
function displayPredictionError(container, data) {
    const warnings = data.warnings || ['Unable to generate prediction'];
    
    container.innerHTML = `
        <div class="prediction-error">
            <p><strong>Cannot Generate Prediction</strong></p>
            <p>${warnings.join('. ')}</p>
            ${data.basis ? `<p style="margin-top:10px; font-size:0.9em;">Data points available: ${data.basis.data_points}</p>` : ''}
        </div>
    `;
}

/**
 * Get confidence dots visualization
 */
function getConfidenceDots(confidence) {
    switch(confidence) {
        case 'High':
            return '●●●●●';
        case 'Medium':
            return '●●●○○';
        case 'Low':
            return '●○○○○';
        default:
            return '○○○○○';
    }
}
