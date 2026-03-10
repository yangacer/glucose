// Form handlers

/**
 * Initialize all form submissions
 */
function initializeForms() {
    // Glucose form
    document.getElementById('glucoseForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn);
        
        const formData = new FormData(e.target);
        const data = {
            timestamp: toDbTimestamp(formData.get('timestamp')),
            level: parseInt(formData.get('level'))
        };
        
        const result = await submitData('/glucose', data);
        resetButton(submitBtn);
        showMessage('glucose-message', result.success, result.message);
        if (result.success) {
            e.target.reset();
            loadGlucoseAudit();
        }
    });

    // Insulin form
    document.getElementById('insulinForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn);
        
        const formData = new FormData(e.target);
        const data = {
            timestamp: toDbTimestamp(formData.get('timestamp')),
            level: parseFloat(formData.get('level'))
        };
        
        const result = await submitData('/insulin', data);
        resetButton(submitBtn);
        showMessage('insulin-message', result.success, result.message);
        if (result.success) {
            e.target.reset();
            loadInsulinAudit();
        }
    });

    // Intake form
    document.getElementById('intakeForm').addEventListener('submit', handleIntakeSubmit);

    // Supplements form
    document.getElementById('supplementsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn);
        
        const formData = new FormData(e.target);
        const data = {
            supplement_name: formData.get('supplement_name'),
            default_amount: parseFloat(formData.get('default_amount'))
        };
        
        const result = await submitData('/supplements', data);
        resetButton(submitBtn);
        showMessage('supplements-message', result.success, result.message);
        if (result.success) {
            e.target.reset();
            e.target.querySelector('input[name="default_amount"]').value = '1';
            loadSupplementsList();
        }
    });

    // Event form
    document.getElementById('eventForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn);
        
        const formData = new FormData(e.target);
        const data = {
            timestamp: toDbTimestamp(formData.get('timestamp')),
            event_name: formData.get('event_name'),
            event_notes: formData.get('event_notes')
        };
        
        const result = await submitData('/event', data);
        resetButton(submitBtn);
        showMessage('event-message', result.success, result.message);
        if (result.success) {
            e.target.reset();
            loadEventAudit();
        }
    });

    // Nutrition form
    document.getElementById('nutritionForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(submitBtn);
        
        const formData = new FormData(e.target);
        const data = {
            nutrition_name: formData.get('nutrition_name'),
            kcal: parseFloat(formData.get('kcal')),
            weight: parseFloat(formData.get('weight'))
        };
        
        const result = await submitData('/nutrition', data);
        resetButton(submitBtn);
        showMessage('nutrition-message', result.success, result.message);
        if (result.success) {
            e.target.reset();
            loadNutritionList();
            loadNutritionAudit();
        }
    });
}

/**
 * Handle intake form submission (nutrition and supplements)
 */
async function handleIntakeSubmit(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setButtonLoading(submitBtn);
    
    const formData = new FormData(e.target);
    const timestamp = toDbTimestamp(formData.get('timestamp'));
    
    // Check if we're in edit mode
    if (window.currentEditingIntakeId) {
        // Edit mode - single nutrition item
        const nutritionId = formData.get('nutrition_id[]');
        const nutritionAmount = formData.get('nutrition_amount[]');
        
        if (!nutritionId) {
            resetButton(submitBtn);
            showMessage('intake-message', false, 'Please select a nutrition item');
            return;
        }
        
        const data = {
            timestamp: timestamp,
            nutrition_id: parseInt(nutritionId),
            nutrition_amount: parseFloat(nutritionAmount)
        };
        
        try {
            const response = await fetch(`${API_BASE}/intake/${window.currentEditingIntakeId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            resetButton(submitBtn);
            if (response.ok) {
                showMessage('intake-message', true, 'Record updated successfully!');
                cancelIntakeEdit();
                loadIntakeAudit();
            } else {
                const error = await response.json();
                showMessage('intake-message', false, error.error || 'Update failed');
            }
        } catch (err) {
            resetButton(submitBtn);
            showMessage('intake-message', false, 'Network error: ' + err.message);
        }
        return;
    }
    
    // Create mode - multiple items
    const nutritionIds = formData.getAll('nutrition_id[]');
    const nutritionAmounts = formData.getAll('nutrition_amount[]');
    const supplementIds = formData.getAll('supplement_id[]');
    const supplementAmounts = formData.getAll('supplement_amount[]');
    
    let allSuccess = true;
    let messages = [];
    
    // Submit nutrition items
    for (let i = 0; i < nutritionIds.length; i++) {
        if (nutritionIds[i]) {
            const data = {
                timestamp: timestamp,
                nutrition_id: parseInt(nutritionIds[i]),
                nutrition_amount: parseFloat(nutritionAmounts[i])
            };
            
            const result = await submitData('/intake', data);
            if (!result.success) {
                allSuccess = false;
                messages.push(`Nutrition Item ${i + 1}: ${result.message}`);
            }
        }
    }
    
    // Submit supplement items
    for (let i = 0; i < supplementIds.length; i++) {
        if (supplementIds[i]) {
            const data = {
                timestamp: timestamp,
                supplement_id: parseInt(supplementIds[i]),
                supplement_amount: parseFloat(supplementAmounts[i])
            };
            
            const result = await submitData('/supplement-intake', data);
            if (!result.success) {
                allSuccess = false;
                messages.push(`Supplement Item ${i + 1}: ${result.message}`);
            }
        }
    }
    
    resetButton(submitBtn);
    if (allSuccess) {
        const totalItems = nutritionIds.filter(id => id).length + supplementIds.filter(id => id).length;
        showMessage('intake-message', true, `Successfully submitted ${totalItems} item(s)!`);
        resetIntakeForm();
        loadIntakeAudit();
        loadSupplementIntakeAudit();
    } else {
        showMessage('intake-message', false, 'Some items failed: ' + messages.join(', '));
    }
}

/**
 * Reset intake form to initial state
 */
function resetIntakeForm() {
    document.getElementById('intakeForm').reset();
    
    // Reset nutrition items
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
    
    // Reset supplement items
    const supplementContainer = document.getElementById('supplement-items-container');
    supplementContainer.innerHTML = `
        <div class="supplement-item nutrition-item">
            <h4>Supplement Item 1</h4>
            <label>Supplement: 
                <select name="supplement_id[]" class="supplement-select" required>
                    <option value="">Select supplement...</option>
                </select>
            </label>
            <label>Amount: <input type="number" name="supplement_amount[]" required min="0" step="0.1"></label>
            <button type="button" class="remove-supplement-btn">Remove</button>
        </div>
    `;
    
    nutritionItemCount = 1;
    supplementItemCount = 1;
    
    // Ensure add buttons are visible
    document.getElementById('add-nutrition-btn').style.display = 'inline-block';
    document.getElementById('add-supplement-btn').style.display = 'inline-block';
    
    // Reset submit button text
    const submitBtn = document.querySelector('#intakeForm button[type="submit"]');
    submitBtn.textContent = 'Submit All';
    submitBtn.classList.remove('update-mode');
    
    // Remove cancel button if exists
    const cancelBtn = document.getElementById('cancel-edit-btn');
    if (cancelBtn) {
        cancelBtn.remove();
    }
    
    // Clear edit mode
    window.currentEditingIntakeId = null;
    
    loadNutritionOptions();
    loadSupplementOptions();
}
