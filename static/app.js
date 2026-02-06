const API_BASE = 'http://localhost:8000/api';

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(targetTab).classList.add('active');
        
        if (targetTab === 'dashboard') {
            loadDashboard();
        } else if (targetTab === 'intake') {
            loadNutritionOptions();
        }
    });
});

// Initialize date inputs with defaults
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

// Form submissions
document.getElementById('glucoseForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        timestamp: formData.get('timestamp').replace('T', ' ') + ':00',
        level: parseInt(formData.get('level'))
    };
    
    const result = await submitData('/glucose', data);
    showMessage('glucose-message', result.success, result.message);
    if (result.success) e.target.reset();
});

document.getElementById('insulinForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        timestamp: formData.get('timestamp').replace('T', ' ') + ':00',
        level: parseFloat(formData.get('level'))
    };
    
    const result = await submitData('/insulin', data);
    showMessage('insulin-message', result.success, result.message);
    if (result.success) e.target.reset();
});

document.getElementById('intakeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        timestamp: formData.get('timestamp').replace('T', ' ') + ':00',
        nutrition_id: parseInt(formData.get('nutrition_id')),
        nutrition_amount: parseFloat(formData.get('nutrition_amount'))
    };
    
    const result = await submitData('/intake', data);
    showMessage('intake-message', result.success, result.message);
    if (result.success) e.target.reset();
});

document.getElementById('supplementsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        timestamp: formData.get('timestamp').replace('T', ' ') + ':00',
        supplement_name: formData.get('supplement_name'),
        supplement_amount: parseFloat(formData.get('supplement_amount'))
    };
    
    const result = await submitData('/supplements', data);
    showMessage('supplements-message', result.success, result.message);
    if (result.success) e.target.reset();
});

document.getElementById('eventForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        timestamp: formData.get('timestamp').replace('T', ' ') + ':00',
        event_name: formData.get('event_name'),
        event_notes: formData.get('event_notes')
    };
    
    const result = await submitData('/event', data);
    showMessage('event-message', result.success, result.message);
    if (result.success) e.target.reset();
});

document.getElementById('nutritionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        nutrition_name: formData.get('nutrition_name'),
        kcal: parseFloat(formData.get('kcal')),
        weight: parseFloat(formData.get('weight'))
    };
    
    const result = await submitData('/nutrition', data);
    showMessage('nutrition-message', result.success, result.message);
    if (result.success) {
        e.target.reset();
        loadNutritionList();
    }
});

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

function showMessage(elementId, success, message) {
    const msgEl = document.getElementById(elementId);
    msgEl.textContent = message;
    msgEl.className = 'message ' + (success ? 'success' : 'error');
    setTimeout(() => {
        msgEl.textContent = '';
        msgEl.className = 'message';
    }, 5000);
}

// Dashboard loading
async function loadDashboard() {
    loadGlucoseChart();
    loadSummary();
    loadNutritionList();
}

let glucoseChart = null;

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

async function loadSummary() {
    const startDate = document.getElementById('summary-start-date').value;
    const endDate = document.getElementById('summary-end-date').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard/summary?start_date=${startDate}&end_date=${endDate}`);
        const data = await response.json();
        
        const tbody = document.getElementById('summaryBody');
        tbody.innerHTML = '';
        
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.am_pm}</td>
                <td>${row.date}</td>
                <td>${row.dose_time || '-'}</td>
                <td>${row.intake_time}</td>
                <td>${row.dosage || '-'}</td>
                <td>${row.nutrition}</td>
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
                <td>${row.grouped_events}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load summary:', err);
    }
}

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

async function loadNutritionOptions() {
    try {
        const response = await fetch(`${API_BASE}/nutrition`);
        const data = await response.json();
        
        const select = document.getElementById('nutrition-select');
        select.innerHTML = '<option value="">Select nutrition...</option>';
        
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = `${item.nutrition_name} (${item.kcal_per_gram.toFixed(4)} kcal/g)`;
            select.appendChild(option);
        });
    } catch (err) {
        console.error('Failed to load nutrition options:', err);
    }
}

// Auto-fill current timestamp for all datetime inputs
function setCurrentTimestamp() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    
    const datetimeLocal = `${year}-${month}-${day}T${hours}:${minutes}`;
    
    document.querySelectorAll('input[type="datetime-local"]').forEach(input => {
        if (!input.value) {
            input.value = datetimeLocal;
        }
    });
}

// Auto-fill timestamps when switching to input tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        setTimeout(setCurrentTimestamp, 100);
    });
});

// Initialize on page load
initializeDateInputs();
loadDashboard();
setCurrentTimestamp();
