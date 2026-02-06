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

// Dynamic nutrition items for intake form
let nutritionItemCount = 1;

document.getElementById('add-nutrition-btn').addEventListener('click', () => {
    nutritionItemCount++;
    const container = document.getElementById('nutrition-items-container');
    const newItem = document.createElement('div');
    newItem.className = 'nutrition-item';
    newItem.innerHTML = `
        <h3>Nutrition Item ${nutritionItemCount}</h3>
        <label>Nutrition: 
            <select name="nutrition_id[]" class="nutrition-select" required>
                <option value="">Select nutrition...</option>
            </select>
        </label>
        <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1"></label>
        <button type="button" class="remove-nutrition-btn">Remove</button>
    `;
    container.appendChild(newItem);
    
    // Load nutrition options for new select
    loadNutritionOptionsForSelect(newItem.querySelector('.nutrition-select'));
    
    // Update remove button visibility
    updateRemoveButtons();
    
    // Add event listener to new remove button
    newItem.querySelector('.remove-nutrition-btn').addEventListener('click', function() {
        newItem.remove();
        updateRemoveButtons();
        renumberNutritionItems();
    });
});

function updateRemoveButtons() {
    const items = document.querySelectorAll('.nutrition-item');
    items.forEach(item => {
        const removeBtn = item.querySelector('.remove-nutrition-btn');
        if (items.length > 1) {
            removeBtn.style.display = 'inline-block';
        } else {
            removeBtn.style.display = 'none';
        }
    });
}

function renumberNutritionItems() {
    const items = document.querySelectorAll('.nutrition-item');
    items.forEach((item, index) => {
        item.querySelector('h3').textContent = `Nutrition Item ${index + 1}`;
    });
    nutritionItemCount = items.length;
}

document.getElementById('intakeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const timestamp = formData.get('timestamp').replace('T', ' ') + ':00';
    const nutritionIds = formData.getAll('nutrition_id[]');
    const nutritionAmounts = formData.getAll('nutrition_amount[]');
    
    let allSuccess = true;
    let messages = [];
    
    // Submit each nutrition item separately with the same timestamp
    for (let i = 0; i < nutritionIds.length; i++) {
        const data = {
            timestamp: timestamp,
            nutrition_id: parseInt(nutritionIds[i]),
            nutrition_amount: parseFloat(nutritionAmounts[i])
        };
        
        const result = await submitData('/intake', data);
        if (!result.success) {
            allSuccess = false;
            messages.push(`Item ${i + 1}: ${result.message}`);
        }
    }
    
    if (allSuccess) {
        showMessage('intake-message', true, `Successfully submitted ${nutritionIds.length} nutrition item(s)!`);
        e.target.reset();
        // Reset to single item
        const container = document.getElementById('nutrition-items-container');
        container.innerHTML = `
            <div class="nutrition-item">
                <h3>Nutrition Item 1</h3>
                <label>Nutrition: 
                    <select name="nutrition_id[]" class="nutrition-select" required>
                        <option value="">Select nutrition...</option>
                    </select>
                </label>
                <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1"></label>
                <button type="button" class="remove-nutrition-btn" style="display:none;">Remove</button>
            </div>
        `;
        nutritionItemCount = 1;
        loadNutritionOptions();
    } else {
        showMessage('intake-message', false, 'Some items failed: ' + messages.join(', '));
    }
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
            if (row) {  // Skip null rows (windows with no data)
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
        
        const selects = document.querySelectorAll('.nutrition-select');
        selects.forEach(select => {
            select.innerHTML = '<option value="">Select nutrition...</option>';
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = `${item.nutrition_name} (${item.kcal_per_gram.toFixed(4)} kcal/g)`;
                select.appendChild(option);
            });
        });
    } catch (err) {
        console.error('Failed to load nutrition options:', err);
    }
}

async function loadNutritionOptionsForSelect(selectElement) {
    try {
        const response = await fetch(`${API_BASE}/nutrition`);
        const data = await response.json();
        
        selectElement.innerHTML = '<option value="">Select nutrition...</option>';
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = `${item.nutrition_name} (${item.kcal_per_gram.toFixed(4)} kcal/g)`;
            selectElement.appendChild(option);
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

// Audit/Edit functionality
async function loadGlucoseAudit() {
    const startDate = document.getElementById('glucose-start-filter').value;
    const endDate = document.getElementById('glucose-end-filter').value;
    
    let url = `${API_BASE}/glucose`;
    if (startDate && endDate) {
        url += `?start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('glucose-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${record.timestamp}</td>
            <td>${record.level}</td>
            <td>
                <button class="edit-btn" onclick="editGlucose(${record.id}, '${record.timestamp}', ${record.level})">Edit</button>
                <button class="delete-btn" onclick="deleteGlucose(${record.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function editGlucose(id, timestamp, level) {
    const newTimestamp = prompt('Enter new timestamp (YYYY-MM-DD HH:MM:SS):', timestamp);
    const newLevel = prompt('Enter new glucose level:', level);
    
    if (newTimestamp && newLevel) {
        const response = await fetch(`${API_BASE}/glucose/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                timestamp: newTimestamp,
                level: parseInt(newLevel)
            })
        });
        
        if (response.ok) {
            alert('Record updated successfully!');
            loadGlucoseAudit();
        } else {
            alert('Failed to update record');
        }
    }
}

async function deleteGlucose(id) {
    if (confirm('Are you sure you want to delete this record?')) {
        const response = await fetch(`${API_BASE}/glucose/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully!');
            loadGlucoseAudit();
        } else {
            alert('Failed to delete record');
        }
    }
}

async function loadInsulinAudit() {
    const startDate = document.getElementById('insulin-start-filter').value;
    const endDate = document.getElementById('insulin-end-filter').value;
    
    let url = `${API_BASE}/insulin`;
    if (startDate && endDate) {
        url += `?start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('insulin-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${record.timestamp}</td>
            <td>${record.level}</td>
            <td>
                <button class="edit-btn" onclick="editInsulin(${record.id}, '${record.timestamp}', ${record.level})">Edit</button>
                <button class="delete-btn" onclick="deleteInsulin(${record.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function editInsulin(id, timestamp, level) {
    const newTimestamp = prompt('Enter new timestamp (YYYY-MM-DD HH:MM:SS):', timestamp);
    const newLevel = prompt('Enter new insulin level:', level);
    
    if (newTimestamp && newLevel) {
        const response = await fetch(`${API_BASE}/insulin/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                timestamp: newTimestamp,
                level: parseFloat(newLevel)
            })
        });
        
        if (response.ok) {
            alert('Record updated successfully!');
            loadInsulinAudit();
        } else {
            alert('Failed to update record');
        }
    }
}

async function deleteInsulin(id) {
    if (confirm('Are you sure you want to delete this record?')) {
        const response = await fetch(`${API_BASE}/insulin/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully!');
            loadInsulinAudit();
        } else {
            alert('Failed to delete record');
        }
    }
}

async function loadIntakeAudit() {
    const startDate = document.getElementById('intake-start-filter').value;
    const endDate = document.getElementById('intake-end-filter').value;
    
    let url = `${API_BASE}/intake`;
    if (startDate && endDate) {
        url += `?start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('intake-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${record.timestamp}</td>
            <td>${record.nutrition_name}</td>
            <td>${record.nutrition_amount}</td>
            <td>${record.nutrition_kcal.toFixed(1)}</td>
            <td>
                <button class="delete-btn" onclick="deleteIntake(${record.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function deleteIntake(id) {
    if (confirm('Are you sure you want to delete this record?')) {
        const response = await fetch(`${API_BASE}/intake/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully!');
            loadIntakeAudit();
        } else {
            alert('Failed to delete record');
        }
    }
}

// Autofill from previous window
async function autofillPreviousIntake() {
    try {
        const response = await fetch(`${API_BASE}/intake/previous-window`);
        const data = await response.json();
        
        if (data.length === 0) {
            return;
        }
        
        const container = document.getElementById('nutrition-items-container');
        container.innerHTML = '';
        nutritionItemCount = 0;
        
        data.forEach((item, index) => {
            nutritionItemCount++;
            const newItem = document.createElement('div');
            newItem.className = 'nutrition-item';
            newItem.innerHTML = `
                <h3>Nutrition Item ${nutritionItemCount}</h3>
                <label>Nutrition: 
                    <select name="nutrition_id[]" class="nutrition-select" required>
                        <option value="">Select nutrition...</option>
                    </select>
                </label>
                <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1" value="${item.nutrition_amount}"></label>
                <button type="button" class="remove-nutrition-btn">Remove</button>
            `;
            container.appendChild(newItem);
            
            loadNutritionOptionsForSelect(newItem.querySelector('.nutrition-select')).then(() => {
                newItem.querySelector('.nutrition-select').value = item.nutrition_id;
            });
            
            newItem.querySelector('.remove-nutrition-btn').addEventListener('click', function() {
                newItem.remove();
                updateRemoveButtons();
                renumberNutritionItems();
            });
        });
        
        updateRemoveButtons();
    } catch (err) {
        console.error('Failed to autofill previous intake:', err);
    }
}

// Load audits when switching to input tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        
        setTimeout(() => {
            if (targetTab === 'glucose') {
                loadGlucoseAudit();
            } else if (targetTab === 'insulin') {
                loadInsulinAudit();
            } else if (targetTab === 'intake') {
                loadIntakeAudit();
                autofillPreviousIntake();
            }
        }, 100);
    });
});
