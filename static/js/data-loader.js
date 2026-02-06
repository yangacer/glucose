// Data loading functionality

/**
 * Load nutrition options for all nutrition selects
 */
async function loadNutritionOptions() {
    try {
        const response = await fetch(`${API_BASE}/nutrition`);
        const data = await response.json();
        
        const selects = document.querySelectorAll('.nutrition-select');
        selects.forEach(select => {
            populateNutritionSelect(select, data);
        });
    } catch (err) {
        console.error('Failed to load nutrition options:', err);
    }
}

/**
 * Load nutrition options for a specific select element
 */
async function loadNutritionOptionsForSelect(selectElement) {
    try {
        const response = await fetch(`${API_BASE}/nutrition`);
        const data = await response.json();
        populateNutritionSelect(selectElement, data);
    } catch (err) {
        console.error('Failed to load nutrition options:', err);
    }
}

/**
 * Populate a nutrition select with data
 */
function populateNutritionSelect(select, data) {
    select.innerHTML = '<option value="">Select nutrition...</option>';
    data.forEach(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = `${item.nutrition_name} (${item.kcal_per_gram.toFixed(4)} kcal/g)`;
        select.appendChild(option);
    });
}

/**
 * Load supplement options for all supplement selects
 */
async function loadSupplementOptions() {
    try {
        const response = await fetch(`${API_BASE}/supplements`);
        const data = await response.json();
        
        const selects = document.querySelectorAll('.supplement-select');
        selects.forEach(select => {
            populateSupplementSelect(select, data);
        });
    } catch (err) {
        console.error('Failed to load supplement options:', err);
    }
}

/**
 * Load supplement options for a specific select element
 */
async function loadSupplementOptionsForSelect(selectElement) {
    try {
        const response = await fetch(`${API_BASE}/supplements`);
        const data = await response.json();
        populateSupplementSelect(selectElement, data);
    } catch (err) {
        console.error('Failed to load supplement options:', err);
    }
}

/**
 * Populate a supplement select with data and add auto-fill listener
 */
function populateSupplementSelect(select, data) {
    select.innerHTML = '<option value="">Select supplement...</option>';
    data.forEach(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = item.supplement_name;
        option.dataset.defaultAmount = item.default_amount;
        select.appendChild(option);
    });
    
    // Auto-fill default amount when supplement is selected
    select.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        const defaultAmount = selectedOption.dataset.defaultAmount;
        if (defaultAmount) {
            const amountInput = this.closest('.supplement-item').querySelector('input[name="supplement_amount[]"]');
            amountInput.value = defaultAmount;
        }
    });
}

/**
 * Load and display supplements list (master table)
 */
async function loadSupplementsList() {
    try {
        const response = await fetch(`${API_BASE}/supplements`);
        const data = await response.json();
        
        const container = document.getElementById('supplements-list');
        if (data.length === 0) {
            container.innerHTML = '<p>No supplements found.</p>';
            return;
        }
        
        let html = '<table><thead><tr><th>ID</th><th>Supplement Name</th><th>Default Amount</th><th>Actions</th></tr></thead><tbody>';
        
        data.forEach(item => {
            html += `
                <tr>
                    <td>${item.id}</td>
                    <td><span class="view-mode">${item.supplement_name}</span>
                        <input type="text" class="edit-mode" style="display:none;" value="${item.supplement_name}" data-field="supplement_name"></td>
                    <td><span class="view-mode">${item.default_amount}</span>
                        <input type="number" class="edit-mode" style="display:none;" value="${item.default_amount}" step="0.1" data-field="default_amount"></td>
                    <td>
                        <button class="edit-btn" data-id="${item.id}">Edit</button>
                        <button class="save-btn" data-id="${item.id}" style="display:none;">Save</button>
                        <button class="cancel-btn" data-id="${item.id}" style="display:none;">Cancel</button>
                        <button class="delete-btn" data-id="${item.id}">Delete</button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
        
        // Add event listeners
        attachSupplementsListListeners(container);
    } catch (err) {
        console.error('Failed to load supplements list:', err);
    }
}

/**
 * Attach event listeners to supplements list buttons
 */
function attachSupplementsListListeners(container) {
    container.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => editSupplementRow(btn.dataset.id));
    });
    
    container.querySelectorAll('.save-btn').forEach(btn => {
        btn.addEventListener('click', () => saveSupplementRow(btn.dataset.id));
    });
    
    container.querySelectorAll('.cancel-btn').forEach(btn => {
        btn.addEventListener('click', () => loadSupplementsList());
    });
    
    container.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteSupplement(btn.dataset.id));
    });
}

/**
 * Auto-fill intake form from previous time window
 */
async function autofillPreviousIntake() {
    try {
        const response = await fetch(`${API_BASE}/intake/previous-window`);
        const data = await response.json();
        
        const nutritionData = data.nutrition || [];
        const supplementData = data.supplements || [];
        
        await populatePreviousNutritionItems(nutritionData);
        await populatePreviousSupplementItems(supplementData);
    } catch (err) {
        console.error('Failed to autofill previous intake:', err);
    }
}

/**
 * Populate nutrition items from previous window
 */
async function populatePreviousNutritionItems(nutritionData) {
    const container = document.getElementById('nutrition-items-container');
    container.innerHTML = '';
    nutritionItemCount = 0;
    
    if (nutritionData.length === 0) {
        addEmptyNutritionItem(container);
    } else {
        for (const item of nutritionData) {
            await addPreviousNutritionItem(container, item);
        }
    }
    
    updateNutritionRemoveButtons();
}

/**
 * Populate supplement items from previous window
 */
async function populatePreviousSupplementItems(supplementData) {
    const container = document.getElementById('supplement-items-container');
    container.innerHTML = '';
    supplementItemCount = 0;
    
    if (supplementData.length === 0) {
        addEmptySupplementItem(container);
    } else {
        for (const item of supplementData) {
            await addPreviousSupplementItem(container, item);
        }
    }
    
    updateSupplementRemoveButtons();
}

/**
 * Add empty nutrition item to container
 */
function addEmptyNutritionItem(container) {
    nutritionItemCount = 1;
    const newItem = document.createElement('div');
    newItem.className = 'nutrition-item';
    newItem.innerHTML = `
        <h4>Nutrition Item 1</h4>
        <label>Nutrition: 
            <select name="nutrition_id[]" class="nutrition-select" required>
                <option value="">Select nutrition...</option>
            </select>
        </label>
        <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1"></label>
        <button type="button" class="remove-nutrition-btn" style="display:none;">Remove</button>
    `;
    container.appendChild(newItem);
    loadNutritionOptionsForSelect(newItem.querySelector('.nutrition-select'));
}

/**
 * Add previous nutrition item to container
 */
async function addPreviousNutritionItem(container, item) {
    nutritionItemCount++;
    const newItem = document.createElement('div');
    newItem.className = 'nutrition-item';
    newItem.innerHTML = `
        <h4>Nutrition Item ${nutritionItemCount}</h4>
        <label>Nutrition: 
            <select name="nutrition_id[]" class="nutrition-select" required>
                <option value="">Select nutrition...</option>
            </select>
        </label>
        <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1" value="${item.nutrition_amount}"></label>
        <button type="button" class="remove-nutrition-btn">Remove</button>
    `;
    container.appendChild(newItem);
    
    await loadNutritionOptionsForSelect(newItem.querySelector('.nutrition-select'));
    newItem.querySelector('.nutrition-select').value = item.nutrition_id;
    
    newItem.querySelector('.remove-nutrition-btn').addEventListener('click', function() {
        newItem.remove();
        updateNutritionRemoveButtons();
        renumberNutritionItems();
    });
}

/**
 * Add empty supplement item to container
 */
function addEmptySupplementItem(container) {
    supplementItemCount = 1;
    const newItem = document.createElement('div');
    newItem.className = 'supplement-item nutrition-item';
    newItem.innerHTML = `
        <h4>Supplement Item 1</h4>
        <label>Supplement: 
            <select name="supplement_id[]" class="supplement-select" required>
                <option value="">Select supplement...</option>
            </select>
        </label>
        <label>Amount: <input type="number" name="supplement_amount[]" required min="0" step="0.1"></label>
        <button type="button" class="remove-supplement-btn" style="display:none;">Remove</button>
    `;
    container.appendChild(newItem);
    loadSupplementOptionsForSelect(newItem.querySelector('.supplement-select'));
}

/**
 * Add previous supplement item to container
 */
async function addPreviousSupplementItem(container, item) {
    supplementItemCount++;
    const newItem = document.createElement('div');
    newItem.className = 'supplement-item nutrition-item';
    newItem.innerHTML = `
        <h4>Supplement Item ${supplementItemCount}</h4>
        <label>Supplement: 
            <select name="supplement_id[]" class="supplement-select" required>
                <option value="">Select supplement...</option>
            </select>
        </label>
        <label>Amount: <input type="number" name="supplement_amount[]" required min="0" step="0.1" value="${item.supplement_amount}"></label>
        <button type="button" class="remove-supplement-btn">Remove</button>
    `;
    container.appendChild(newItem);
    
    await loadSupplementOptionsForSelect(newItem.querySelector('.supplement-select'));
    newItem.querySelector('.supplement-select').value = item.supplement_id;
    
    newItem.querySelector('.remove-supplement-btn').addEventListener('click', function() {
        newItem.remove();
        updateSupplementRemoveButtons();
        renumberSupplementItems();
    });
}
