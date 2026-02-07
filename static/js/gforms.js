/**
 * GForms Menu Functionality
 * Handles submissions loading, category management, and field mappings.
 */

document.addEventListener('DOMContentLoaded', function () {
    // Only initialize if we are on the GForms tab or if the partial is loaded
    const gformsTab = document.getElementById('list-gforms');
    if (!gformsTab) return;

    const eventId = document.querySelector('[data-event-id]')?.dataset.eventId;
    if (!eventId) return;

    // --- State ---
    let categories = [];
    let fieldMappings = [];
    let currentPage = 1;
    let totalPages = 1;

    // --- Initialization ---

    // Load initial data when tab is shown
    const tabTrigger = document.getElementById('list-gforms-list');
    if (tabTrigger) {
        tabTrigger.addEventListener('shown.bs.tab', function () {
            loadAllData(eventId);
        });
    }

    // Refresh buttons
    document.querySelectorAll('.refresh-gforms-btn').forEach(btn => {
        btn.addEventListener('click', () => loadAllData(eventId));
    });

    // --- Data Loading ---

    function loadAllData(eventId) {
        loadCategories(eventId)
            .then(() => loadFieldMappings(eventId))
            .then(() => loadSubmissions(eventId, 1));
    }

    function loadCategories(eventId) {
        return fetch(`/event/${eventId}/gforms/categories`)
            .then(response => response.json())
            .then(data => {
                categories = data.categories;
                renderCategoriesList();
                renderCategorySelectors();
                return categories;
            })
            .catch(err => console.error('Error loading categories:', err));
    }

    function loadFieldMappings(eventId) {
        return fetch(`/event/${eventId}/gforms/fields`)
            .then(response => response.json())
            .then(data => {
                fieldMappings = data.fields;
                renderFieldMappings();
                return fieldMappings;
            })
            .catch(err => console.error('Error loading fields:', err));
    }

    function loadSubmissions(eventId, page) {
        const tbody = document.getElementById('gforms-table-body');
        if (!tbody) return;

        tbody.innerHTML = '<tr><td colspan="5" class="text-center"><div class="spinner-border text-primary" role="status"></div></td></tr>';

        fetch(`/event/${eventId}/gforms/submissions?page=${page}&per_page=50`)
            .then(response => response.json())
            .then(data => {
                renderSubmissionsTable(data.submissions);
                renderPagination(data.pagination);
                currentPage = data.pagination.page;
                totalPages = data.pagination.pages;
            })
            .catch(err => {
                console.error('Error loading submissions:', err);
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Erreur lors du chargement des données</td></tr>';
            });
    }

    // --- Rendering ---

    function renderSubmissionsTable(submissions) {
        const tbody = document.getElementById('gforms-table-body');
        const thead = document.getElementById('gforms-table-head');

        if (!tbody || !thead) return;

        tbody.innerHTML = '';

        if (submissions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="100%" class="text-center text-muted">Aucun formulaire reçu pour le moment</td></tr>';
            return;
        }

        // 1. Determine all unique columns from all submissions (for dynamic headers)
        // We rely on the backend provided fields list ideally, but here we can also infer
        // For simplicity, let's assume we collected all possible fields in loadFieldMappings logic
        // But for the table headers, we need to be consistent.

        // Let's use the fieldMappings which contains all detected fields
        const dynamicFields = fieldMappings.map(f => f.field_name);

        // Update Header
        let headerHTML = `
            <tr>
                <th>Email</th>
                <th>Timestamp</th>
                <th>Type d'ajout</th>
        `;

        dynamicFields.forEach(field => {
            // Find category for color
            const mapping = fieldMappings.find(m => m.field_name === field);
            const category = mapping && mapping.category ? mapping.category : null;
            const colorClass = category ? `text-${category.color}-emphasis bg-${category.color}-subtle` : '';

            headerHTML += `<th class="${colorClass}">${field}</th>`;
        });

        headerHTML += '</tr>';
        thead.innerHTML = headerHTML;

        // Update Body
        submissions.forEach(sub => {
            const tr = document.createElement('tr');

            // Type badge
            let badgeClass = 'bg-secondary';
            if (sub.type_ajout === 'créé') badgeClass = 'bg-success';
            else if (sub.type_ajout === 'ajouté') badgeClass = 'bg-info text-dark';
            else if (sub.type_ajout === 'mis à jour') badgeClass = 'bg-warning text-dark';

            let html = `
                <td>${sub.email}</td>
                <td>${sub.timestamp}</td>
                <td><span class="badge ${badgeClass}">${sub.type_ajout || '-'}</span></td>
            `;

            dynamicFields.forEach(field => {
                const value = sub.raw_data[field] !== undefined ? sub.raw_data[field] : '';

                // Find category for cell color
                const mapping = fieldMappings.find(m => m.field_name === field);
                const category = mapping && mapping.category ? mapping.category : null;
                const cellClass = category ? `bg-${category.color}-subtle` : '';

                // Truncate long text
                const displayValue = String(value).length > 50 ? String(value).substring(0, 50) + '...' : value;
                const fullValue = String(value).replace(/"/g, '&quot;');

                html += `<td class="${cellClass}" title="${fullValue}">${displayValue}</td>`;
            });

            tr.innerHTML = html;
            tbody.appendChild(tr);
        });
    }

    function renderPagination(pagination) {
        const container = document.getElementById('gforms-pagination');
        if (!container) return;

        // Simple pagination buttons
        let html = `
            <span class="me-3">Page ${pagination.page} sur ${pagination.pages} (${pagination.total} résultats)</span>
            <div class="btn-group">
                <button class="btn btn-outline-secondary btn-sm" ${!pagination.has_prev ? 'disabled' : ''} onclick="loadSubmissions('${eventId}', ${pagination.page - 1})">
                    <i class="bi bi-chevron-left"></i> Précédent
                </button>
                <button class="btn btn-outline-secondary btn-sm" ${!pagination.has_next ? 'disabled' : ''} onclick="loadSubmissions('${eventId}', ${pagination.page + 1})">
                    Suivant <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;
        container.innerHTML = html;

        // Expose function globally for the onclick handlers
        window.loadSubmissions = loadSubmissions;
    }

    function renderCategoriesList() {
        const container = document.getElementById('categories-list');
        if (!container) return;

        container.innerHTML = '';

        categories.forEach((cat, index) => {
            const div = document.createElement('div');
            div.className = 'row mb-2 category-row align-items-center';
            div.dataset.id = cat.id;

            const isDefault = cat.name === 'Généralités';

            div.innerHTML = `
                <div class="col-md-4">
                    <input type="text" class="form-control category-name" value="${cat.name}" required ${isDefault ? 'readonly' : ''}>
                </div>
                <div class="col-md-4">
                    <select class="form-select category-color">
                        ${getColorOptions(cat.color)}
                    </select>
                </div>
                <div class="col-md-2 text-center">
                    <div class="color-preview bg-${cat.color}-subtle border" style="width: 30px; height: 30px; border-radius: 4px; display: inline-block;"></div>
                </div>
                <div class="col-md-2">
                    ${!isDefault ? `
                    <button class="btn btn-outline-danger btn-sm remove-category-btn">
                        <i class="bi bi-trash"></i>
                    </button>` : ''}
                </div>
            `;

            container.appendChild(div);

            // Event listeners
            const colorSelect = div.querySelector('.category-color');
            const preview = div.querySelector('.color-preview');

            colorSelect.addEventListener('change', function () {
                // Update preview class
                const newColor = this.value;
                preview.className = `color-preview bg-${newColor}-subtle border`;
                preview.style.display = 'inline-block';
                preview.style.width = '30px';
                preview.style.height = '30px';
            });

            const removeBtn = div.querySelector('.remove-category-btn');
            if (removeBtn) {
                removeBtn.addEventListener('click', function () {
                    div.remove();
                });
            }
        });
    }

    function getColorOptions(selectedColor) {
        const colors = [
            { value: 'neutral', label: 'Neutre (Gris)' },
            { value: 'blue', label: 'Bleu' },
            { value: 'green', label: 'Vert' },
            { value: 'red', label: 'Rouge' },
            { value: 'yellow', label: 'Jaune' },
            { value: 'purple', label: 'Violet' },
            { value: 'orange', label: 'Orange' },
            { value: 'pink', label: 'Rose' },
            { value: 'teal', label: 'Turquoise' }
        ];

        return colors.map(c =>
            `<option value="${c.value}" ${c.value === selectedColor ? 'selected' : ''}>${c.label}</option>`
        ).join('');
    }

    function renderFieldMappings() {
        const tbody = document.getElementById('field-mappings-body');
        if (!tbody) return;

        tbody.innerHTML = '';

        // Filter out system fields for simpler display if desired, or keep them with readonly nature
        // User requested: "timestamp" and "type_ajout" should also be configurable
        // Backend get_fields returns them too.

        fieldMappings.forEach(field => {
            const tr = document.createElement('tr');
            const mapping = field;

            tr.innerHTML = `
                <td>
                    <span class="badge bg-secondary text-wrap text-start" style="font-size: 0.9em;">${field.field_name}</span>
                </td>
                <td>
                    <select class="form-select mapping-category-select" data-field="${field.field_name}">
                        <option value="">-- Non catégorisé --</option>
                        ${getCategoryOptions(field.category_id)}
                    </select>
                </td>
            `;

            tbody.appendChild(tr);
        });
    }

    function getCategoryOptions(selectedId) {
        return categories.map(cat =>
            `<option value="${cat.id}" ${cat.id === selectedId ? 'selected' : ''}>${cat.name}</option>`
        ).join('');
    }

    function renderCategorySelectors() {
        // Re-render mapping selectors if categories changed
        // ... (Already handled by full re-fetch usually, but could be optimized)
    }

    // --- Actions ---

    // Add Category
    const addCategoryBtn = document.getElementById('add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', function () {
            const container = document.getElementById('categories-list');
            const div = document.createElement('div');
            div.className = 'row mb-2 category-row align-items-center';

            div.innerHTML = `
                <div class="col-md-4">
                    <input type="text" class="form-control category-name" placeholder="Nom de la catégorie" required>
                </div>
                <div class="col-md-4">
                    <select class="form-select category-color">
                        ${getColorOptions('neutral')}
                    </select>
                </div>
                <div class="col-md-2 text-center">
                    <div class="color-preview bg-neutral-subtle border" style="width: 30px; height: 30px; border-radius: 4px; display: inline-block;"></div>
                </div>
                <div class="col-md-2">
                    <button class="btn btn-outline-danger btn-sm remove-category-btn">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;

            container.appendChild(div);

            // Listeners for new row
            div.querySelector('.category-color').addEventListener('change', function () {
                const preview = div.querySelector('.color-preview');
                preview.className = `color-preview bg-${this.value}-subtle border`;
            });
            div.querySelector('.remove-category-btn').addEventListener('click', function () {
                div.remove();
            });
        });
    }

    // Save Categories
    const saveCategoriesBtn = document.getElementById('save-categories-btn');
    if (saveCategoriesBtn) {
        saveCategoriesBtn.addEventListener('click', function () {
            const rows = document.querySelectorAll('.category-row');
            const categoriesData = [];

            rows.forEach(row => {
                const nameInput = row.querySelector('.category-name');
                const colorSelect = row.querySelector('.category-color');
                const id = row.dataset.id ? parseInt(row.dataset.id) : null;

                if (nameInput && nameInput.value.trim()) {
                    categoriesData.push({
                        id: id,
                        name: nameInput.value.trim(),
                        color: colorSelect.value
                    });
                }
            });

            fetch(`/event/${eventId}/gforms/categories`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value
                },
                body: JSON.stringify({ categories: categoriesData })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Reload everything to reflect changes
                        loadAllData(eventId);
                        alert('Catégories enregistrées avec succès');
                    } else {
                        alert('Erreur: ' + data.error);
                    }
                })
                .catch(err => console.error('Error saving categories:', err));
        });
    }

    // Save Mappings
    const saveMappingsBtn = document.getElementById('save-mappings-btn');
    if (saveMappingsBtn) {
        saveMappingsBtn.addEventListener('click', function () {
            const selects = document.querySelectorAll('.mapping-category-select');
            const mappingsData = [];

            selects.forEach(select => {
                mappingsData.push({
                    field_name: select.dataset.field,
                    category_id: select.value ? parseInt(select.value) : null
                });
            });

            fetch(`/event/${eventId}/gforms/field-mappings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value
                },
                body: JSON.stringify({ mappings: mappingsData })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loadAllData(eventId);
                        alert('Mappings enregistrés avec succès');
                    } else {
                        alert('Erreur: ' + data.error);
                    }
                })
                .catch(err => console.error('Error saving mappings:', err));
        });
    }
});
