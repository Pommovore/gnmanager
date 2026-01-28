document.addEventListener('DOMContentLoaded', function () {
    const castingContainer = document.getElementById('casting-container');
    if (!castingContainer) return;

    const eventId = castingContainer.dataset.eventId;
    // Handle root path correctly
    const baseUrl = (typeof SCRIPT_ROOT !== 'undefined' && SCRIPT_ROOT === '/') ? '' : (SCRIPT_ROOT || '');

    let castingData = null;
    let roles = []; // Original roles list
    let groupsConfig = {}; // For dynamic filtering

    // Filter state
    let filters = {
        type: '',
        group: '',
        genre: ''
    };

    // Get CSRF token from meta tag
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }

    // Load casting data
    function loadCastingData() {
        const spinner = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Chargement...</p></div>';

        // Only show spinner if first load (container has no content or just spinner)
        if (!document.getElementById('castingTabs')) {
            castingContainer.innerHTML = spinner;
        }

        fetch(`${baseUrl}/event/${eventId}/casting_data`)
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`Server error: ${response.status} ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                castingData = data;
                roles = data.roles || []; // Get roles from API
                groupsConfig = data.groups_config || {};
                renderCastingTable();
            })
            .catch(error => {
                console.error('Error loading casting data:', error);
                castingContainer.innerHTML = '<div class="alert alert-danger">Erreur lors du chargement des données.</div>';
            });
    }

    // Render the casting interface
    function renderCastingTable() {
        try {
            // Render basic structure if not exists
            if (!document.getElementById('castingTabs')) {
                const template = document.getElementById('casting-content-template');
                if (!template) {
                    throw new Error('Template HTML introuvable (casting-content-template)');
                }
                castingContainer.innerHTML = '';
                castingContainer.appendChild(template.content.cloneNode(true));
            }

            renderRolesView();
            renderParticipantsView();
            attachFilterListeners();
            attachEventListeners();
            updateValidationSwitchState();
        } catch (error) {
            console.error('Error rendering casting table:', error);
            castingContainer.innerHTML = `<div class="alert alert-danger">
                Erreur d'affichage des données: ${error.message}
            </div>`;
        }
    }

    // Render Roles Table (Tab 1)
    function renderRolesView() {
        // Apply filters
        const filteredRoles = roles.filter(role => {
            const matchesType = !filters.type || role.type === filters.type;
            const matchesGroup = !filters.group || role.group === filters.group;
            const matchesGenre = !filters.genre || role.genre === filters.genre;
            return matchesType && matchesGroup && matchesGenre;
        });

        const container = document.getElementById('roles-table-container');
        const template = document.getElementById('roles-table-template');
        container.innerHTML = '';

        const clone = template.content.cloneNode(true);

        // Calculate total roles by type (for main column counter)
        const totalRolesByType = { 'PJ': 0, 'PNJ': 0, 'Organisateur': 0 };
        roles.forEach(role => {
            if (totalRolesByType.hasOwnProperty(role.type)) {
                totalRolesByType[role.type]++;
            }
        });

        // Count assigned roles in main column
        const mainAssignedByType = { 'PJ': 0, 'PNJ': 0, 'Organisateur': 0 };
        Object.entries(castingData.assignments['main'] || {}).forEach(([roleId, participantId]) => {
            if (participantId) {
                const role = roles.find(r => r.id === parseInt(roleId));
                if (role && mainAssignedByType.hasOwnProperty(role.type)) {
                    mainAssignedByType[role.type]++;
                }
            }
        });

        // Update main column counter
        const remainingMainPJ = totalRolesByType['PJ'] - mainAssignedByType['PJ'];
        const remainingMainPNJ = totalRolesByType['PNJ'] - mainAssignedByType['PNJ'];
        const remainingMainOrga = totalRolesByType['Organisateur'] - mainAssignedByType['Organisateur'];

        const mainCounter = clone.querySelector('#main-roles-counter');
        if (mainCounter) {
            mainCounter.textContent = `(reste PJ:${remainingMainPJ} PNJ:${remainingMainPNJ} O:${remainingMainOrga})`;
        }

        // Add proposal columns to header
        const headerRow = clone.querySelector('thead tr');
        castingData.proposals.forEach(proposal => {
            const proposalId = proposal.id.toString();
            const proposalAssignments = castingData.assignments[proposalId] || {};

            // Count total participants by type
            const totalParticipantsByType = { 'PJ': 0, 'PNJ': 0, 'Organisateur': 0 };
            Object.entries(castingData.participants_by_type).forEach(([type, participants]) => {
                if (totalParticipantsByType.hasOwnProperty(type)) {
                    totalParticipantsByType[type] = participants.length;
                }
            });

            // Count assigned participants in this proposal by type
            const assignedParticipantsByType = { 'PJ': 0, 'PNJ': 0, 'Organisateur': 0 };
            const assignedParticipantIds = new Set(Object.values(proposalAssignments).filter(id => id));

            Object.entries(castingData.participants_by_type).forEach(([type, participants]) => {
                if (assignedParticipantsByType.hasOwnProperty(type)) {
                    assignedParticipantsByType[type] = participants.filter(p => assignedParticipantIds.has(p.id)).length;
                }
            });

            // Calculate remaining participants
            const remainingPJ = totalParticipantsByType['PJ'] - assignedParticipantsByType['PJ'];
            const remainingPNJ = totalParticipantsByType['PNJ'] - assignedParticipantsByType['PNJ'];
            const remainingOrga = totalParticipantsByType['Organisateur'] - assignedParticipantsByType['Organisateur'];

            const th = document.createElement('th');
            th.style.minWidth = '250px';
            th.innerHTML = `
                ${proposal.name}
                <small class="text-muted ms-2">(${remainingPJ}/${remainingPNJ}/${remainingOrga})</small>
                <button class="btn btn-sm btn-outline-danger ms-2 delete-proposal-btn" data-proposal-id="${proposal.id}">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            headerRow.appendChild(th);
        });

        // Add role rows
        const tbody = clone.querySelector('#casting-tbody');
        filteredRoles.forEach(role => {
            const tr = document.createElement('tr');

            // Role info cell
            const roleCell = document.createElement('td');
            roleCell.innerHTML = `
                <strong>${role.name}</strong><br>
                <small class="text-muted">${role.type || 'Tous'} - ${role.genre || 'Tous'}</small>
            `;
            tr.appendChild(roleCell);

            // Main assignment cell
            const mainCell = document.createElement('td');
            mainCell.innerHTML = createAssignmentDropdown('main', role.id, role.type, castingData.assignments['main'][role.id]);
            tr.appendChild(mainCell);

            // Proposal cells
            castingData.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                const proposalId = proposal.id.toString();
                const participantId = castingData.assignments[proposalId]?.[role.id];
                const score = castingData.scores[proposalId]?.[role.id];

                cell.innerHTML = `
                    <div class="d-flex flex-column gap-1">
                        ${createAssignmentDropdown(proposalId, role.id, role.type, participantId)}
                        ${createScoreSlider(proposalId, role.id, score)}
                    </div>
                `;
                tr.appendChild(cell);
            });

            tbody.appendChild(tr);
        });

        container.appendChild(clone);
    }

    // Render Participants Table (Tab 2)
    function renderParticipantsView() {
        const participantsTable = document.getElementById('participants-table');
        if (!participantsTable) return;

        const headerRow = participantsTable.querySelector('thead tr');
        const tbody = participantsTable.querySelector('#participants-tbody');

        // Reset header (keep first 2 columns: Participant, Main Assignment)
        while (headerRow.children.length > 2) {
            headerRow.removeChild(headerRow.lastChild);
        }

        // Add proposal columns
        castingData.proposals.forEach(proposal => {
            const th = document.createElement('th');
            th.style.minWidth = '250px';
            th.textContent = proposal.name;
            headerRow.appendChild(th);
        });

        // Flatten participants list (preserve type information)
        let allParticipants = [];
        for (const [type, participants] of Object.entries(castingData.participants_by_type)) {
            // Add type to each participant for display
            const participantsWithType = participants.map(p => ({ ...p, type: type }));
            allParticipants = allParticipants.concat(participantsWithType);
        }
        // Sort by name
        allParticipants.sort((a, b) => a.nom.localeCompare(b.nom));

        tbody.innerHTML = '';

        allParticipants.forEach(p => {
            const tr = document.createElement('tr');

            // Participant info cell
            const participantCell = document.createElement('td');
            participantCell.innerHTML = `
                <strong>${p.nom} ${p.prenom}</strong> <small class="text-muted">(${p.type})</small>
            `;
            tr.appendChild(participantCell);

            // Find assignments for this participant
            // Main assignment
            let mainRoleId = null;
            for (const [roleId, assignedPId] of Object.entries(castingData.assignments['main'])) {
                if (assignedPId === p.id) {
                    mainRoleId = roleId;
                    break;
                }
            }

            const mainCell = document.createElement('td');
            mainCell.innerHTML = createRoleDropdown('main', p.id, mainRoleId);
            tr.appendChild(mainCell);

            // Proposals
            castingData.proposals.forEach(proposal => {
                const proposalId = proposal.id.toString();
                let assignedRoleId = null;
                const proposalAssignments = castingData.assignments[proposalId] || {};

                for (const [roleId, assignedPId] of Object.entries(proposalAssignments)) {
                    if (assignedPId === p.id) {
                        assignedRoleId = roleId;
                        break;
                    }
                }

                const cell = document.createElement('td');
                cell.innerHTML = createRoleDropdown(proposalId, p.id, assignedRoleId);
                tr.appendChild(cell);
            });

            tbody.appendChild(tr);
        });
    }

    // Create ROLE dropdown (for Participants tab)
    function createRoleDropdown(proposalId, participantId, selectedRoleId) {
        let options = '<option value="">-- Aucun rôle --</option>';

        // Create map of assigned roles in this proposal to exclude them
        const assignedRoles = new Set();
        const assignments = castingData.assignments[proposalId] || {};
        for (const [rId, pId] of Object.entries(assignments)) {
            // If role is assigned AND it is NOT assigned to CURRENT participant
            // (Wait: we want to only hide roles assigned to OTHERS)
            // If pId matches current participantId, it IS the current assignment, so we keep it available (implicitly handled by logic below)
            if (pId && parseInt(pId) !== parseInt(participantId)) {
                assignedRoles.add(parseInt(rId));
            }
        }

        roles.forEach(role => {
            // Only show if unassigned OR assigned to this participant
            if (!assignedRoles.has(role.id)) {
                // Determine if this is the selected role
                // Note: role.id is int, selectedRoleId might be string from keys
                const isSelected = selectedRoleId && (parseInt(role.id) === parseInt(selectedRoleId));
                const selectedAttr = isSelected ? 'selected' : '';
                options += `<option value="${role.id}" ${selectedAttr}>${role.name}</option>`;
            }
        });

        return `
            <select class="form-select form-select-sm role-select" 
                data-proposal-id="${proposalId}" 
                data-participant-id="${participantId}">
                ${options}
            </select>
        `;
    }

    // Create assignment dropdown HTML (for Roles tab)
    function createAssignmentDropdown(proposalId, roleId, roleType, selectedParticipantId) {
        let options = '<option value="">-- Non attribué --</option>';

        // Get participants already assigned in this proposal (exclude from list)
        const assignedParticipantIds = new Set();
        if (castingData.assignments && castingData.assignments[proposalId]) {
            Object.values(castingData.assignments[proposalId]).forEach(participantId => {
                // Don't exclude the currently selected participant (allow re-assignment)
                if (participantId && participantId !== selectedParticipantId) {
                    assignedParticipantIds.add(participantId);
                }
            });
        }

        // Filter participants by role type AND availability
        const matchingParticipants = castingData.participants_by_type[roleType] || [];

        matchingParticipants.forEach(p => {
            // Skip if already assigned to another role in this proposal
            if (assignedParticipantIds.has(p.id)) {
                return;
            }

            const selected = p.id === selectedParticipantId ? 'selected' : '';
            options += `<option value="${p.id}" ${selected}>${p.nom} ${p.prenom}</option>`;
        });

        return `
        <select class="form-select form-select-sm assignment-select" 
            data-proposal-id="${proposalId}" 
            data-role-id="${roleId}">
            ${options}
        </select>
    `;
    }

    // Create score slider HTML
    function createScoreSlider(proposalId, roleId, selectedScore) {
        const score = (selectedScore !== null && selectedScore !== undefined) ? selectedScore : 0;
        const color = getScoreColor(score);

        return `
            <div class="score-slider-container mt-1 pt-2 border-top d-flex align-items-center gap-2">
                <small class="text-muted fw-bold" style="font-size: 0.7rem;">Score</small>
                <input type="range" class="form-range score-slider" 
                    min="0" max="10" step="1" 
                    value="${score}"
                    data-proposal-id="${proposalId}"
                    data-role-id="${roleId}"
                    style="flex-grow: 1; margin-top: 0;">
                <span class="badge score-badge" style="background-color: ${color}; min-width: 25px;">${score}</span>
            </div>
        `;
    }

    function getScoreColor(score) {
        if (score === null || score === undefined) return '#6c757d';
        // HSL: 0 is red, 120 is green
        const hue = score * 12;
        return `hsl(${hue}, 70%, 45%)`;
    }

    // Shared update function
    function updateAssignment(proposalId, roleId, participantId) {
        // Handle unassignment from Participants tab (roleId is empty)
        if (!roleId && participantId) {
            // We need to find which role this participant currently has in this proposal to unassign it
            // Actually, we can just look up the assignment by searching assignments map.
            // But the backend endpoint expects role_id.

            // Search in local data
            const assignments = castingData.assignments[proposalId] || {};
            for (const [rId, pId] of Object.entries(assignments)) {
                if (parseInt(pId) === parseInt(participantId)) {
                    roleId = rId;
                    break;
                }
            }

            if (!roleId) return; // Nothing to unassign
            participantId = null; // Explicitly nullify
        }

        fetch(`${baseUrl}/event/${eventId}/casting/assign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                proposal_id: proposalId === 'main' ? 'main' : parseInt(proposalId),
                role_id: parseInt(roleId),
                participant_id: participantId ? parseInt(participantId) : null
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadCastingData();
                } else {
                    alert('Erreur lors de l\'attribution');
                }
            });
    }

    // Attach event listeners
    function attachEventListeners() {
        // Assignment dropdowns (Roles Tab)
        // Use event delegation or re-attach
        // Here we clear container so re-attaching is fine

        document.querySelectorAll('.assignment-select').forEach(select => {
            select.addEventListener('change', function () {
                const proposalId = this.dataset.proposalId;
                const roleId = this.dataset.roleId;
                const participantId = this.value || null;

                updateAssignment(proposalId, roleId, participantId);
            });
        });

        // Role dropdowns (Participants Tab)
        document.querySelectorAll('.role-select').forEach(select => {
            select.addEventListener('change', function () {
                const proposalId = this.dataset.proposalId;
                const participantId = this.dataset.participantId;
                const roleId = this.value || null;

                updateAssignment(proposalId, roleId, participantId);
            });
        });

        // Score sliders
        document.querySelectorAll('.score-slider').forEach(slider => {
            slider.addEventListener('input', function () {
                // Visual feedback during sliding
                const score = this.value;
                const container = this.closest('.score-slider-container');
                const badge = container.querySelector('.score-badge');
                badge.textContent = score;
                badge.style.backgroundColor = getScoreColor(parseInt(score));
            });

            slider.addEventListener('change', function () {
                const proposalId = this.dataset.proposalId;
                const roleId = this.dataset.roleId;
                const score = this.value;

                fetch(`${baseUrl}/event/${eventId}/casting/update_score`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({
                        proposal_id: parseInt(proposalId),
                        role_id: parseInt(roleId),
                        score: parseInt(score)
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (!data.success) {
                            alert('Erreur lors de la mise à jour du score');
                        }
                    });
            });
        });

        // Add proposal button
        const addBtn = document.getElementById('add-proposal-btn');
        if (addBtn) {
            const newAddBtn = addBtn.cloneNode(true);
            addBtn.parentNode.replaceChild(newAddBtn, addBtn);

            newAddBtn.addEventListener('click', function () {
                const name = prompt('Nom de la proposition:');
                if (name) {
                    fetch(`${baseUrl}/event/${eventId}/casting/add_proposal`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({ name: name })
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.id) {
                                loadCastingData();
                            } else {
                                alert(data.error || 'Erreur');
                            }
                        });
                }
            });
        }

        // Delete proposal buttons (delegation or direct)
        document.querySelectorAll('.delete-proposal-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                const proposalId = this.dataset.proposalId;
                if (confirm('Supprimer cette proposition ?')) {
                    fetch(`${baseUrl}/event/${eventId}/casting/delete_proposal`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({ proposal_id: parseInt(proposalId) })
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                loadCastingData();
                            } else {
                                alert(data.error || 'Erreur');
                            }
                        });
                }
            });
        });

        // Auto-Assign (Hungarian Algorithm) Button
        const autoAssignBtn = document.getElementById('auto-assign-btn');
        if (autoAssignBtn) {
            const newAutoBtn = autoAssignBtn.cloneNode(true);
            autoAssignBtn.parentNode.replaceChild(newAutoBtn, autoAssignBtn);

            newAutoBtn.addEventListener('click', function () {
                if (confirm('Voulez-vous lancer l\'attribution automatique optimale (Algorithme Hongrois) ?\nCela remplacera les attributions actuelles de la colonne principale basee sur les scores.')) {
                    const btnHtml = this.innerHTML;
                    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Calcul...';
                    this.disabled = true;

                    fetch(`${baseUrl}/event/${eventId}/casting/auto_assign`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        }
                    })
                        .then(response => response.json())
                        .then(data => {
                            this.innerHTML = btnHtml;
                            this.disabled = false;

                            if (data.success) {
                                alert(`Attribution terminée !\n${data.assigned_count}/${data.total_roles} rôles attribués.`);
                                loadCastingData();
                            } else {
                                alert(data.error || 'Erreur lors du calcul');
                            }
                        })
                        .catch(err => {
                            console.error('Error:', err);
                            this.innerHTML = btnHtml;
                            this.disabled = false;
                            alert('Erreur serveur lors du calcul.');
                        });
                }
            });
        }

        const validationSwitch = document.getElementById('castingValidationSwitch');
        const validationLabel = document.getElementById('castingValidationLabel');
        if (validationSwitch) {
            // Clone to remove old listeners just in case
            const newSwitch = validationSwitch.cloneNode(true);
            validationSwitch.parentNode.replaceChild(newSwitch, validationSwitch);

            newSwitch.addEventListener('change', function () {
                const validated = this.checked;

                fetch(`${baseUrl}/event/${eventId}/casting/toggle_validation`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ validated: validated })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            if (data.is_casting_validated) {
                                validationLabel.innerHTML = '<span class="badge bg-success">Validé</span>';
                            } else {
                                validationLabel.innerHTML = '<span class="badge bg-secondary">Non-validé</span>';
                            }
                        } else {
                            this.checked = !this.checked;
                            alert('Erreur lors de la mise à jour');
                        }
                    })
                    .catch(() => {
                        this.checked = !this.checked;
                        alert('Erreur lors de la mise à jour');
                    });
            });
        }
    }

    // Filter Listeners
    function attachFilterListeners() {
        const filterType = document.getElementById('filter-type');
        const filterGroup = document.getElementById('filter-group');
        const filterGenre = document.getElementById('filter-genre');

        if (filterType) {
            // Set current values
            filterType.value = filters.type;
            filterType.addEventListener('change', function () {
                filters.type = this.value;
                filters.group = ''; // Reset group when type changes
                updateGroupOptions();
                renderCastingTable();
            });
        }

        if (filterGroup) {
            updateGroupOptions();
            filterGroup.value = filters.group;
            filterGroup.addEventListener('change', function () {
                filters.group = this.value;
                renderCastingTable();
            });
        }

        if (filterGenre) {
            filterGenre.value = filters.genre;
            filterGenre.addEventListener('change', function () {
                filters.genre = this.value;
                renderCastingTable();
            });
        }
    }

    function updateGroupOptions() {
        const filterGroup = document.getElementById('filter-group');
        if (!filterGroup) return;

        const currentGroup = filters.group;
        filterGroup.innerHTML = '<option value="">Peu importe</option>';
        if (filters.type && groupsConfig[filters.type]) {
            groupsConfig[filters.type].forEach(group => {
                const option = document.createElement('option');
                option.value = group;
                option.textContent = group;
                if (group === currentGroup) option.selected = true;
                filterGroup.appendChild(option);
            });
        }
    }


    function updateValidationSwitchState() {
        const validationSwitch = document.getElementById('castingValidationSwitch');
        const validationLabel = document.getElementById('castingValidationLabel');
        if (validationSwitch && castingData) {
            validationSwitch.checked = !!castingData.is_casting_validated;
            if (castingData.is_casting_validated) {
                validationLabel.innerHTML = '<span class="badge bg-success">Validé</span>';
            } else {
                validationLabel.innerHTML = '<span class="badge bg-secondary">Non-validé</span>';
            }
        }
    }

    // Initial load
    loadCastingData();
});
