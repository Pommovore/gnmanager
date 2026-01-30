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
});
