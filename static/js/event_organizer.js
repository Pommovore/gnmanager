// event_organizer.js - Gestion générale de l'interface organisateur
// Ce fichier gère les tooltips, la navigation entre onglets et la configuration dynamique des groupes

document.addEventListener('DOMContentLoaded', function () {
    // Groups configuration from server - récupéré depuis le data attribute
    const groupsConfigElement = document.getElementById('groups-config-data');
    const groupsConfig = groupsConfigElement ? JSON.parse(groupsConfigElement.textContent) : {};

    // Handle all type selects (add form and edit modals)
    document.querySelectorAll('.role-type-select').forEach(function (typeSelect) {
        typeSelect.addEventListener('change', function () {
            const target = this.dataset.target;
            const groupSelect = document.getElementById(target + '-group-select');
            const selectedType = this.value;
            const currentGroup = groupSelect.dataset.current || '';

            // Clear existing options
            groupSelect.innerHTML = '<option value="">Aucun groupe</option>';

            if (selectedType && groupsConfig[selectedType]) {
                groupSelect.disabled = false;
                groupsConfig[selectedType].forEach(function (grp) {
                    const option = document.createElement('option');
                    option.value = grp;
                    option.textContent = grp;
                    if (grp === currentGroup) {
                        option.selected = true;
                    }
                    groupSelect.appendChild(option);
                });
            } else {
                groupSelect.disabled = true;
            }
        });

        // Trigger change on page load for edit modals with existing type
        if (typeSelect.value) {
            typeSelect.dispatchEvent(new Event('change'));
        }
    });

    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Activate tab from URL hash (for redirect after role creation/update or sidebar clicks)
    function activateTabFromHash() {
        const hash = window.location.hash;
        if (hash) {
            // Find tab trigger by href (handles both #hash and full_url#hash)
            const tabTrigger = document.querySelector('[data-bs-toggle="list"][href="' + hash + '"]');
            if (tabTrigger) {
                const tab = new bootstrap.Tab(tabTrigger);
                tab.show();
            }
        }
    }

    // Initial activation
    activateTabFromHash();

    // Activation on hash change (useful if user clicks sidebar link on same page)
    window.addEventListener('hashchange', activateTabFromHash);

    // Roles tab filtering logic
    const roleFilterType = document.getElementById('role-filter-type');
    const roleFilterGroup = document.getElementById('role-filter-group');
    const roleFilterGenre = document.getElementById('role-filter-genre');
    const roleTable = document.getElementById('role-management-table');

    if (roleFilterType && roleFilterGroup && roleFilterGenre && roleTable) {
        const rows = roleTable.querySelectorAll('tbody tr');

        function applyFilters() {
            const typeValue = roleFilterType.value;
            const groupValue = roleFilterGroup.value;
            const genreValue = roleFilterGenre.value;

            rows.forEach(row => {
                const rowType = row.dataset.type || '';
                const rowGroup = row.dataset.group || '';
                const rowGenre = row.dataset.genre || '';

                const matchesType = !typeValue || rowType === typeValue;
                const matchesGroup = !groupValue || rowGroup === groupValue;
                const matchesGenre = !genreValue || rowGenre === genreValue;

                if (matchesType && matchesGroup && matchesGenre) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        roleFilterType.addEventListener('change', function () {
            const selectedType = this.value;

            // Update group filter options
            roleFilterGroup.innerHTML = '<option value="">Peu importe</option>';
            if (selectedType && groupsConfig[selectedType]) {
                groupsConfig[selectedType].forEach(grp => {
                    const option = document.createElement('option');
                    option.value = grp;
                    option.textContent = grp;
                    roleFilterGroup.appendChild(option);
                });
            }

            applyFilters();
        });

        roleFilterGroup.addEventListener('change', applyFilters);
        roleFilterGenre.addEventListener('change', applyFilters);

        // Sorting Logic for Roles Management Table
        const sortButtons = roleTable.querySelectorAll('.role-sort-btn');
        let currentSort = { column: null, direction: 'asc' };

        sortButtons.forEach(btn => {
            btn.addEventListener('click', function () {
                const column = this.dataset.sort;

                // Toggle direction if same column, else reset to asc
                if (currentSort.column === column) {
                    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.column = column;
                    currentSort.direction = 'asc';
                }

                // Update icons
                sortButtons.forEach(b => {
                    const icon = b.querySelector('i');
                    icon.className = 'bi bi-arrow-down-up';
                    b.classList.remove('text-primary');
                    b.classList.add('text-light');
                });
                const activeIcon = this.querySelector('i');
                activeIcon.className = currentSort.direction === 'asc' ? 'bi bi-sort-alpha-down' : 'bi bi-sort-alpha-up';
                this.classList.remove('text-light');
                this.classList.add('text-primary');

                // Sort Rows
                const tbody = roleTable.querySelector('tbody');
                const rowsArray = Array.from(tbody.querySelectorAll('tr'));

                rowsArray.sort((a, b) => {
                    let valA = '', valB = '';

                    // Extract values based on column
                    switch (column) {
                        case 'name':
                            valA = a.cells[0].textContent.trim().toLowerCase();
                            valB = b.cells[0].textContent.trim().toLowerCase();
                            break;
                        case 'type':
                            // Use data attribute if available or text
                            valA = (a.dataset.type || a.cells[1].textContent.trim()).toLowerCase();
                            valB = (b.dataset.type || b.cells[1].textContent.trim()).toLowerCase();
                            break;
                        case 'genre':
                            valA = (a.dataset.genre || a.cells[2].textContent.trim()).toLowerCase();
                            valB = (b.dataset.genre || b.cells[2].textContent.trim()).toLowerCase();
                            break;
                        case 'group':
                            valA = (a.dataset.group || a.cells[3].textContent.trim()).toLowerCase();
                            valB = (b.dataset.group || b.cells[3].textContent.trim()).toLowerCase();
                            break;
                    }

                    if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
                    if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
                    return 0;
                });

                // Re-append sorted rows
                rowsArray.forEach(row => tbody.appendChild(row));

                // Re-apply filters to ensure correct visibility state is maintained (though sorting shouldn't change visibility)
                // applyFilters(); 
            });
        });

        // Sorting Logic for P.A.F. Management Table
        const pafTable = document.getElementById('paf-management-table');
        if (pafTable) {
            const pafSortButtons = pafTable.querySelectorAll('.paf-sort-btn');
            let currentPafSort = { column: null, direction: 'asc' };

            pafSortButtons.forEach(btn => {
                btn.addEventListener('click', function () {
                    const column = this.dataset.sort;

                    // Toggle logic
                    if (currentPafSort.column === column) {
                        currentPafSort.direction = currentPafSort.direction === 'asc' ? 'desc' : 'asc';
                    } else {
                        currentPafSort.column = column;
                        currentPafSort.direction = 'asc';
                    }

                    // Update icons
                    pafSortButtons.forEach(b => {
                        const icon = b.querySelector('i');
                        icon.className = 'bi bi-arrow-down-up';
                        b.classList.remove('text-primary');
                        b.classList.add('text-light');
                    });
                    const activeIcon = this.querySelector('i');
                    activeIcon.className = currentPafSort.direction === 'asc' ? 'bi bi-sort-alpha-down' : 'bi bi-sort-alpha-up';
                    this.classList.remove('text-light');
                    this.classList.add('text-primary');

                    // Sort Rows
                    const tbody = pafTable.querySelector('tbody');
                    const rowsArray = Array.from(tbody.querySelectorAll('tr'));

                    rowsArray.sort((a, b) => {
                        let valA, valB;

                        // Helper for currency extraction
                        const getCurrency = (cell) => {
                            const text = cell.textContent.replace('€', '').replace(',', '.').trim();
                            return parseFloat(text) || 0;
                        };

                        // Helper for select value
                        const getSelectValue = (cell) => {
                            const select = cell.querySelector('select');
                            return select ? select.value.trim().toLowerCase() : '';
                        };

                        switch (column) {
                            case 'participant': // Col 0
                                valA = a.cells[0].textContent.trim().toLowerCase();
                                valB = b.cells[0].textContent.trim().toLowerCase();
                                break;
                            case 'status': // Col 2
                                valA = a.cells[2].textContent.trim().toLowerCase();
                                valB = b.cells[2].textContent.trim().toLowerCase();
                                break;
                            case 'paid': // Col 3 (Numeric)
                                valA = getCurrency(a.cells[3]);
                                valB = getCurrency(b.cells[3]);
                                break;
                            case 'type': // Col 4 (Select)
                                valA = getSelectValue(a.cells[4]);
                                valB = getSelectValue(b.cells[4]);
                                break;
                            case 'method': // Col 5 (Select)
                                valA = getSelectValue(a.cells[5]);
                                valB = getSelectValue(b.cells[5]);
                                break;
                            case 'due': // Col 6 (Numeric)
                                valA = getCurrency(a.cells[6]);
                                valB = getCurrency(b.cells[6]);
                                break;
                            case 'remaining': // Col 7 (Numeric)
                                valA = getCurrency(a.cells[7]);
                                valB = getCurrency(b.cells[7]);
                                break;
                            default:
                                return 0;
                        }

                        if (valA < valB) return currentPafSort.direction === 'asc' ? -1 : 1;
                        if (valA > valB) return currentPafSort.direction === 'asc' ? 1 : -1;
                        return 0;
                    });

                    // Re-append sorted rows
                    rowsArray.forEach(row => tbody.appendChild(row));
                });
            });
        }
    }
});
