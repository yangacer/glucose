// Dynamic nutrition and supplement item management

let nutritionItemCount = 1;
let supplementItemCount = 1;

/**
 * Initialize add/remove buttons for dynamic items
 */
function initializeDynamicItems() {
    document.getElementById('add-nutrition-btn').addEventListener('click', addNutritionItem);
    document.getElementById('add-supplement-btn').addEventListener('click', addSupplementItem);

    document.getElementById('nutrition-items-container').addEventListener('click', e => {
        if (e.target.matches('.remove-nutrition-btn')) {
            e.target.closest('.nutrition-item').remove();
            renumberNutritionItems();
        }
    });

    document.getElementById('supplement-items-container').addEventListener('click', e => {
        if (e.target.matches('.remove-supplement-btn')) {
            e.target.closest('.supplement-item').remove();
            updateSupplementRemoveButtons();
            renumberSupplementItems();
        }
    });
}

/**
 * Add a new nutrition item to the form
 */
function addNutritionItem() {
    nutritionItemCount++;
    const container = document.getElementById('nutrition-items-container');
    const newItem = document.createElement('div');
    newItem.className = 'nutrition-item';
    newItem.innerHTML = `
        <h4>Nutrition Item ${nutritionItemCount}</h4>
        <label>Nutrition: 
            <select name="nutrition_id[]" class="nutrition-select" required>
                <option value="">Select nutrition...</option>
            </select>
        </label>
        <label>Amount (gram): <input type="number" name="nutrition_amount[]" required min="0" step="0.1"></label>
        <button type="button" class="remove-nutrition-btn">Remove</button>
    `;
    container.appendChild(newItem);
    
    loadNutritionOptionsForSelect(newItem.querySelector('.nutrition-select'));
    updateNutritionRemoveButtons();
}


/**
 * Add a new supplement item to the form
 */
function addSupplementItem() {
    supplementItemCount++;
    const container = document.getElementById('supplement-items-container');
    const newItem = document.createElement('div');
    newItem.className = 'supplement-item nutrition-item';
    newItem.innerHTML = `
        <h4>Supplement Item ${supplementItemCount}</h4>
        <label>Supplement: 
            <select name="supplement_id[]" class="supplement-select" required>
                <option value="">Select supplement...</option>
            </select>
        </label>
        <label>Amount: <input type="number" name="supplement_amount[]" required min="0" step="0.1"></label>
        <button type="button" class="remove-supplement-btn">Remove</button>
    `;
    container.appendChild(newItem);
    
    loadSupplementOptionsForSelect(newItem.querySelector('.supplement-select'));
    updateSupplementRemoveButtons();
}


/**
 * Update visibility of nutrition remove buttons
 */
function updateNutritionRemoveButtons() {
    const items = document.querySelectorAll('#nutrition-items-container .nutrition-item');
    items.forEach(item => {
        const removeBtn = item.querySelector('.remove-nutrition-btn');
        removeBtn.style.display = 'inline-block';
    });
}

/**
 * Update visibility of supplement remove buttons
 */
function updateSupplementRemoveButtons() {
    const items = document.querySelectorAll('#supplement-items-container .supplement-item');
    items.forEach(item => {
        const removeBtn = item.querySelector('.remove-supplement-btn');
        removeBtn.style.display = 'inline-block';
    });
}

/**
 * Renumber nutrition items after removal
 */
function renumberNutritionItems() {
    const items = document.querySelectorAll('#nutrition-items-container .nutrition-item');
    items.forEach((item, index) => {
        item.querySelector('h4').textContent = `Nutrition Item ${index + 1}`;
    });
    nutritionItemCount = items.length;
}

/**
 * Renumber supplement items after removal
 */
function renumberSupplementItems() {
    const items = document.querySelectorAll('#supplement-items-container .supplement-item');
    items.forEach((item, index) => {
        item.querySelector('h4').textContent = `Supplement Item ${index + 1}`;
    });
    supplementItemCount = items.length;
}
