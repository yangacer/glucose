// Audit and Edit functionality

/**
 * Load glucose audit/edit list
 */
async function loadGlucoseAudit() {
    const startDate = document.getElementById('glucose-start-filter').value;
    const endDate = document.getElementById('glucose-end-filter').value;
    
    let url = `${API_BASE}/glucose?tz=${encodeURIComponent(getClientTz())}`;
    if (startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('glucose-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${formatTimestamp(record.timestamp)}</td>
            <td>${record.level}</td>
            <td>
                <button class="edit-btn" data-id="${record.id}" data-ts="${record.timestamp}" data-level="${record.level}">Edit</button>
                <button class="delete-btn" data-id="${record.id}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => editGlucose(btn.dataset.id, btn.dataset.ts, btn.dataset.level));
    });
    tbody.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteGlucose(btn.dataset.id));
    });
}

/**
 * Edit glucose record
 */
async function editGlucose(id, timestamp, level) {
    const newTimestamp = prompt('Enter new timestamp (local time, YYYY-MM-DDTHH:MM):', toInputTimestamp(timestamp));
    const newLevel = prompt('Enter new glucose level:', level);
    
    if (newTimestamp && newLevel) {
        const response = await fetch(`${API_BASE}/glucose/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                timestamp: toDbTimestamp(newTimestamp),
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

/**
 * Delete glucose record
 */
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

/**
 * Load insulin audit/edit list
 */
async function loadInsulinAudit() {
    const startDate = document.getElementById('insulin-start-filter').value;
    const endDate = document.getElementById('insulin-end-filter').value;
    
    let url = `${API_BASE}/insulin?tz=${encodeURIComponent(getClientTz())}`;
    if (startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('insulin-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${formatTimestamp(record.timestamp)}</td>
            <td>${record.level}</td>
            <td>
                <button class="edit-btn" data-id="${record.id}" data-ts="${record.timestamp}" data-level="${record.level}">Edit</button>
                <button class="delete-btn" data-id="${record.id}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => editInsulin(btn.dataset.id, btn.dataset.ts, btn.dataset.level));
    });
    tbody.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteInsulin(btn.dataset.id));
    });
}

/**
 * Edit insulin record
 */
async function editInsulin(id, timestamp, level) {
    const newTimestamp = prompt('Enter new timestamp (local time, YYYY-MM-DDTHH:MM):', toInputTimestamp(timestamp));
    const newLevel = prompt('Enter new insulin level:', level);
    
    if (newTimestamp && newLevel) {
        const response = await fetch(`${API_BASE}/insulin/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                timestamp: toDbTimestamp(newTimestamp),
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

/**
 * Delete insulin record
 */
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

/**
 * Load intake (nutrition) audit list
 */
async function loadIntakeAudit() {
    const startDate = document.getElementById('intake-start-filter').value;
    const endDate = document.getElementById('intake-end-filter').value;
    
    let url = `${API_BASE}/intake?tz=${encodeURIComponent(getClientTz())}`;
    if (startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('intake-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${formatTimestamp(record.timestamp)}</td>
            <td>${record.nutrition_name}</td>
            <td>${record.nutrition_amount}</td>
            <td>${record.nutrition_kcal.toFixed(1)}</td>
            <td>
                <button class="edit-btn"
                    data-id="${record.id}"
                    data-ts="${record.timestamp}"
                    data-nid="${record.nutrition_id}"
                    data-name="${escapeHtml(record.nutrition_name)}"
                    data-amount="${record.nutrition_amount}">Edit</button>
                <button class="delete-btn" data-id="${record.id}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => editIntake(
            btn.dataset.id, btn.dataset.ts, btn.dataset.nid,
            btn.dataset.name, btn.dataset.amount
        ));
    });
    tbody.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteIntake(btn.dataset.id));
    });
}

/**
 * Edit intake record - populates form with existing values
 */
async function editIntake(id, timestamp, nutritionId, nutritionName, nutritionAmount) {
    // Store the record ID being edited
    window.currentEditingIntakeId = id;
    
    // Clear and set up form for single item edit
    const nutritionContainer = document.getElementById('nutrition-items-container');
    nutritionContainer.innerHTML = `
        <div class="nutrition-item">
            <h4>Nutrition Item 1</h4>
            <label>Nutrition: 
                <select name="nutrition_id[]" class="nutrition-select" required>
                    <option value="">Select nutrition...</option>
                </select>
            </label>
            <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1"></label>
            <button type="button" class="remove-nutrition-btn" style="display:none;">Remove</button>
        </div>
    `;
    
    // Clear supplements section for edit mode
    const supplementContainer = document.getElementById('supplement-items-container');
    supplementContainer.innerHTML = '';
    
    // Hide add buttons during edit
    document.getElementById('add-nutrition-btn').style.display = 'none';
    document.getElementById('add-supplement-btn').style.display = 'none';
    
    // Load nutrition options and set selected value
    await loadNutritionOptions();
    const nutritionSelect = document.querySelector('.nutrition-select');
    nutritionSelect.value = nutritionId;
    
    // Set timestamp
    const timestampInput = document.getElementById('intake-timestamp');
    timestampInput.value = toInputTimestamp(timestamp);
    
    // Set amount
    const amountInput = document.querySelector('input[name="nutrition_amount[]"]');
    amountInput.value = nutritionAmount;
    
    // Change submit button to Update
    const submitBtn = document.querySelector('#intakeForm button[type="submit"]');
    submitBtn.textContent = 'Update';
    submitBtn.classList.add('update-mode');
    
    // Add cancel button if not exists
    if (!document.getElementById('cancel-edit-btn')) {
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.id = 'cancel-edit-btn';
        cancelBtn.textContent = 'Cancel Edit';
        cancelBtn.className = 'secondary-btn';
        cancelBtn.addEventListener('click', cancelIntakeEdit);
        submitBtn.parentNode.insertBefore(cancelBtn, submitBtn.nextSibling);
    }
    
    // Scroll to form
    document.getElementById('intake').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Cancel intake edit mode and return to create mode
 */
function cancelIntakeEdit() {
    window.currentEditingIntakeId = null;
    resetIntakeForm();
    
    // Show add buttons
    document.getElementById('add-nutrition-btn').style.display = 'inline-block';
    document.getElementById('add-supplement-btn').style.display = 'inline-block';
    
    // Change button back to Submit
    const submitBtn = document.querySelector('#intakeForm button[type="submit"]');
    submitBtn.textContent = 'Submit All';
    submitBtn.classList.remove('update-mode');
    
    // Remove cancel button
    const cancelBtn = document.getElementById('cancel-edit-btn');
    if (cancelBtn) {
        cancelBtn.remove();
    }
}

/**
 * Delete intake record
 */
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

/**
 * Load supplement intake audit list
 */
async function loadSupplementIntakeAudit() {
    const startDate = document.getElementById('supplement-intake-start-filter').value;
    const endDate = document.getElementById('supplement-intake-end-filter').value;
    
    let url = `${API_BASE}/supplement-intake?tz=${encodeURIComponent(getClientTz())}`;
    if (startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('supplement-intake-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${formatTimestamp(record.timestamp)}</td>
            <td>${record.supplement_name}</td>
            <td>${record.supplement_amount}</td>
            <td>
                <button class="delete-btn" data-id="${record.id}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteSupplementIntake(btn.dataset.id));
    });
}

/**
 * Delete supplement intake record
 */
async function deleteSupplementIntake(id) {
    if (confirm('Are you sure you want to delete this record?')) {
        const response = await fetch(`${API_BASE}/supplement-intake/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully!');
            loadSupplementIntakeAudit();
        } else {
            alert('Failed to delete record');
        }
    }
}

/**
 * Load event audit list
 */
async function loadEventAudit() {
    const startDate = document.getElementById('event-start-filter').value;
    const endDate = document.getElementById('event-end-filter').value;
    
    let url = `${API_BASE}/event?tz=${encodeURIComponent(getClientTz())}`;
    if (startDate && endDate) {
        url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    
    const response = await fetch(url);
    const data = await response.json();
    
    const tbody = document.getElementById('event-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${formatTimestamp(record.timestamp)}</td>
            <td>${record.event_name}</td>
            <td>${record.event_notes || ''}</td>
            <td>
                <button class="delete-btn" data-id="${record.id}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteEvent(btn.dataset.id));
    });
}

/**
 * Delete event record
 */
async function deleteEvent(id) {
    if (confirm('Are you sure you want to delete this record?')) {
        const response = await fetch(`${API_BASE}/event/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully!');
            loadEventAudit();
        } else {
            alert('Failed to delete record');
        }
    }
}

/**
 * Load nutrition master audit list
 */
async function loadNutritionAudit() {
    const response = await fetch(`${API_BASE}/nutrition`);
    const data = await response.json();
    
    const tbody = document.getElementById('nutrition-audit-body');
    tbody.innerHTML = '';
    
    data.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${record.id}</td>
            <td>${record.nutrition_name}</td>
            <td>${record.kcal}</td>
            <td>${record.weight}</td>
            <td>${record.kcal_per_gram.toFixed(4)}</td>
            <td>
                <button class="delete-btn" data-id="${record.id}">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteNutritionItem(btn.dataset.id));
    });
}

/**
 * Delete nutrition item
 */
async function deleteNutritionItem(id) {
    if (confirm('Are you sure you want to delete this nutrition item?')) {
        const response = await fetch(`${API_BASE}/nutrition/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Record deleted successfully!');
            loadNutritionAudit();
            loadNutritionList();
        } else {
            alert('Failed to delete record');
        }
    }
}

/**
 * Edit supplement via prompt dialogs
 */
async function editSupplement(id, name, defaultAmount) {
    const newName = prompt('Enter supplement name:', name);
    if (newName === null) return;
    const newAmount = prompt('Enter default amount:', defaultAmount);
    if (newAmount === null) return;

    try {
        const response = await fetch(`${API_BASE}/supplements/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ supplement_name: newName, default_amount: parseFloat(newAmount) })
        });

        if (response.ok) {
            loadSupplementsList();
        } else {
            alert('Failed to update supplement');
        }
    } catch (err) {
        console.error('Failed to update supplement:', err);
        alert('Failed to update supplement');
    }
}

/**
 * Delete supplement
 */
async function deleteSupplement(id) {
    if (!confirm('Are you sure you want to delete this supplement?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/supplements/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadSupplementsList();
        } else {
            alert('Failed to delete supplement');
        }
    } catch (err) {
        console.error('Failed to delete supplement:', err);
        alert('Failed to delete supplement');
    }
}

