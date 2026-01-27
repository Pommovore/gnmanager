/**
 * Participant Management - Dynamic Group Selection
 * Updates group options in edit modals based on participant type
 */

document.addEventListener('DOMContentLoaded', function () {
    // Load groups configuration from JSON script tag
    const groupsConfigEl = document.getElementById('groups-config-data');
    if (!groupsConfigEl) return;

    const groupsConfig = JSON.parse(groupsConfigEl.textContent);

    // Get all modals
    const modals = document.querySelectorAll('.modal');

    modals.forEach(modal => {
        modal.addEventListener('show.bs.modal', function () {
            const groupSelect = this.querySelector('select[name="group"]');
            const typeSelect = this.querySelector('select[name="type"]');

            if (groupSelect && typeSelect) {
                // Function to update group options
                const updateGroupOptions = () => {
                    const selectedType = typeSelect.value;
                    const currentValue = groupSelect.value;

                    // Clear current options
                    groupSelect.innerHTML = '';

                    // Get groups for this type
                    let groups = [];
                    if (selectedType === 'PJ') groups = groupsConfig.PJ || [];
                    else if (selectedType === 'PNJ') groups = groupsConfig.PNJ || [];
                    else if (selectedType === 'organisateur') groups = groupsConfig.Organisateur || [];

                    // Default if empty
                    if (groups.length === 0) groups = ['Peu importe'];

                    // Populate options
                    groups.forEach(g => {
                        const opt = document.createElement('option');
                        opt.value = g;
                        opt.textContent = g;
                        if (g === currentValue) opt.selected = true;
                        groupSelect.appendChild(opt);
                    });

                    // If current value not in list, add it as first option and select it
                    if (currentValue && !groups.includes(currentValue)) {
                        const opt = document.createElement('option');
                        opt.value = currentValue;
                        opt.textContent = currentValue + ' (actuel)';
                        opt.selected = true;
                        groupSelect.insertBefore(opt, groupSelect.firstChild);
                    }
                };

                // Update on type change
                typeSelect.addEventListener('change', updateGroupOptions);

                // Initial population
                updateGroupOptions();
            }
        });
    });
});
