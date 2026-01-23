// casting.js - Gestion du casting pour GN Manager
// Ce fichier gère toute la logique de l'onglet Casting

document.addEventListener('DOMContentLoaded', function () {
    // Récupérer les variables depuis les data attributes du DOM
    const castingContainer = document.getElementById('casting-container');
    if (!castingContainer) return;

    const eventId = castingContainer.dataset.eventId;
    const csrfToken = castingContainer.dataset.csrfToken;

    // Participants data grouped by type
    let participantsByType = {};
    let proposals = [];
    let assignments = {};
    let scores = {};

    // Load casting data on tab show
    const castingTab = document.querySelector('a[href="#casting-container"]');
    if (castingTab) {
        castingTab.addEventListener('shown.bs.tab', loadCastingData);
        // Also load if already active
        if (castingTab.classList.contains('active')) {
            loadCastingData();
        }
    }

    async function loadCastingData() {
        try {
            const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting_data`);
            const data = await response.json();

            participantsByType = data.participants_by_type;
            proposals = data.proposals;
            assignments = data.assignments;
            scores = data.scores || {};

            // Build proposal columns
            rebuildProposalColumns();

            // Populate all dropdowns
            populateAllDropdowns();

        } catch (error) {
            console.error('Error loading casting data:', error);
        }
    }

    function rebuildProposalColumns() {
        const headerRow = document.querySelector('#casting-table thead tr');
        const bodyRows = document.querySelectorAll('#casting-table tbody tr');

        // Remove existing dynamic proposal columns (keep first 3: Rôle, Type, Attribution)
        headerRow.querySelectorAll('th.dynamic-proposal').forEach(th => th.remove());
        bodyRows.forEach(row => {
            row.querySelectorAll('td.dynamic-proposal').forEach(td => td.remove());
        });

        // Add proposal columns
        proposals.forEach(proposal => {
            // Header
            const th = document.createElement('th');
            th.style.minWidth = '200px';
            th.className = 'proposal-column dynamic-proposal';
            th.dataset.proposalId = proposal.id;
            th.innerHTML = `
                ${proposal.name}
                <button class="btn btn-sm btn-outline-danger ms-2 delete-proposal-btn" 
                        data-proposal-id="${proposal.id}" title="Supprimer cette proposition">
                    <i class="bi bi-x"></i>
                </button>
            `;
            headerRow.appendChild(th);

            // Body cells
            bodyRows.forEach(row => {
                const roleId = row.dataset.roleId;
                const roleType = row.dataset.roleType;
                const td = document.createElement('td');
                td.className = 'assignment-cell dynamic-proposal';
                td.dataset.proposalId = proposal.id;
                td.innerHTML = `
                    <div class="d-flex gap-2 align-items-center">
                        <select class="form-select form-select-sm casting-select flex-grow-1" 
                                data-role-id="${roleId}" 
                                data-proposal-id="${proposal.id}"
                                data-role-type="${roleType}">
                            <option value="">-- Non attribué --</option>
                        </select>
                        <select class="form-select form-select-sm score-select" 
                                style="width: 70px;"
                                data-role-id="${roleId}" 
                                data-proposal-id="${proposal.id}"
                                title="Score (0-10)">
                            ${[...Array(11).keys()].map(i => `<option value="${i}">${i}</option>`).join('')}
                        </select>
                    </div>
                `;
                row.appendChild(td);
            });
        });

        // Add event listeners to new delete buttons
        document.querySelectorAll('.delete-proposal-btn').forEach(btn => {
            btn.addEventListener('click', deleteProposal);
        });
    }

    function populateAllDropdowns() {
        document.querySelectorAll('.casting-select').forEach(select => {
            const roleId = select.dataset.roleId;
            const proposalId = select.dataset.proposalId;

            // Get already assigned participant IDs for this proposal (excluding current role)
            const assignedIds = getAssignedParticipantIds(proposalId, roleId);

            // Clear and repopulate with ALL participants grouped by type
            select.innerHTML = '<option value="">-- Non attribué --</option>';

            // Add all participants grouped by their type
            for (const [type, participants] of Object.entries(participantsByType)) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = type;

                participants.forEach(p => {
                    // Skip if already assigned to another role in this proposal
                    if (assignedIds.includes(p.id)) return;

                    const option = document.createElement('option');
                    option.value = p.id;
                    option.textContent = `${p.nom} ${p.prenom}`;
                    optgroup.appendChild(option);
                });

                // Only add optgroup if it has options
                if (optgroup.childElementCount > 0) {
                    select.appendChild(optgroup);
                }
            }

            // Set current value if assigned
            const currentAssignment = getAssignment(proposalId, roleId);
            if (currentAssignment) {
                select.value = currentAssignment;
            }
        });

        // Add change event listeners
        document.querySelectorAll('.casting-select').forEach(select => {
            select.removeEventListener('change', handleAssignmentChange);
            select.addEventListener('change', handleAssignmentChange);
        });

        // Populate and add change event listeners for scores
        document.querySelectorAll('.score-select').forEach(scoreSelect => {
            const roleId = scoreSelect.dataset.roleId;
            const proposalId = scoreSelect.dataset.proposalId;

            // Skip 'main' proposal as it doesn't have scores
            if (proposalId === 'main') {
                return;
            }

            // Get current score (default to 0, handling 0 as valid value)
            let currentScore = 0;
            if (scores[proposalId] && scores[proposalId][roleId] !== undefined) {
                currentScore = scores[proposalId][roleId];
            }
            scoreSelect.value = currentScore;

            // Add event listener for score changes
            scoreSelect.removeEventListener('change', handleScoreChange);
            scoreSelect.addEventListener('change', handleScoreChange);
        });
    }

    function getAssignedParticipantIds(proposalId, excludeRoleId) {
        const assigned = [];
        const proposalAssignments = assignments[proposalId] || {};
        for (const [roleId, participantId] of Object.entries(proposalAssignments)) {
            if (roleId !== excludeRoleId && participantId) {
                assigned.push(parseInt(participantId));
            }
        }
        return assigned;
    }

    function getAssignment(proposalId, roleId) {
        return assignments[proposalId]?.[roleId] || null;
    }

    async function handleAssignmentChange(event) {
        const select = event.target;
        const roleId = select.dataset.roleId;
        const proposalId = select.dataset.proposalId;
        const participantId = select.value || null;

        try {
            const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting/assign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    role_id: roleId,
                    proposal_id: proposalId,
                    participant_id: participantId
                })
            });

            if (response.ok) {
                // Update local assignments
                if (!assignments[proposalId]) {
                    assignments[proposalId] = {};
                }
                assignments[proposalId][roleId] = participantId;

                // Refresh all dropdowns for this proposal to update available options
                populateAllDropdowns();
            } else {
                console.error('Failed to save assignment');
                // Revert the change
                loadCastingData();
            }
        } catch (error) {
            console.error('Error saving assignment:', error);
            loadCastingData();
        }
    }

    async function handleScoreChange(event) {
        const scoreSelect = event.target;
        const roleId = scoreSelect.dataset.roleId;
        const proposalId = scoreSelect.dataset.proposalId;
        const score = parseInt(scoreSelect.value);

        try {
            const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting/update_score`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    role_id: roleId,
                    proposal_id: proposalId,
                    score: score
                })
            });

            if (response.ok) {
                // Update local scores
                if (!scores[proposalId]) {
                    scores[proposalId] = {};
                }
                scores[proposalId][roleId] = score;
            } else {
                console.error('Failed to save score');
                // Revert the change
                loadCastingData();
            }
        } catch (error) {
            console.error('Error saving score:', error);
            loadCastingData();
        }
    }

    // Add proposal button
    const addProposalBtn = document.getElementById('add-proposal-btn');
    if (addProposalBtn) {
        addProposalBtn.addEventListener('click', async function () {
            const nameInput = document.getElementById('new-proposal-name');
            const name = nameInput.value.trim();

            if (!name) {
                nameInput.classList.add('is-invalid');
                return;
            }
            nameInput.classList.remove('is-invalid');

            try {
                const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting/add_proposal`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ name: name })
                });

                if (response.ok) {
                    nameInput.value = '';
                    loadCastingData();
                } else {
                    alert('Erreur lors de la création de la proposition');
                }
            } catch (error) {
                console.error('Error adding proposal:', error);
            }
        });
    }

    async function deleteProposal(event) {
        const proposalId = event.currentTarget.dataset.proposalId;

        if (!confirm('Supprimer cette proposition et toutes ses attributions ?')) {
            return;
        }

        try {
            const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting/delete_proposal`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ proposal_id: proposalId })
            });

            if (response.ok) {
                loadCastingData();
            } else {
                alert('Erreur lors de la suppression');
            }
        } catch (error) {
            console.error('Error deleting proposal:', error);
        }
    }

    // Auto-assign button
    const autoAssignBtn = document.getElementById('auto-assign-btn');
    if (autoAssignBtn) {
        autoAssignBtn.addEventListener('click', async function () {
            if (!confirm('Calculer les attributions automatiquement en fonction des scores ?\\n\\nCela écrasera les attributions actuelles dans la colonne "Attribution".')) {
                return;
            }

            try {
                const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting/auto_assign`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                if (response.ok) {
                    const result = await response.json();
                    alert(`Attribution automatique terminée !\\n${result.assigned_count} rôles attribués sur ${result.total_roles}.`);
                    loadCastingData();
                } else {
                    const error = await response.json();
                    alert(`Erreur : ${error.error || 'Erreur lors du calcul'}`);
                }
            } catch (error) {
                console.error('Error auto-assigning:', error);
                alert('Erreur lors du calcul automatique');
            }
        });
    }

    // Casting validation switch
    const validationSwitch = document.getElementById('castingValidationSwitch');
    const validationLabel = document.getElementById('castingValidationLabel');

    if (validationSwitch) {
        validationSwitch.addEventListener('change', async function () {
            const validated = this.checked;

            try {
                const response = await fetch(`${SCRIPT_ROOT}/event/${eventId}/casting/toggle_validation`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ validated: validated })
                });

                const data = await response.json();
                if (data.success) {
                    if (data.is_casting_validated) {
                        validationLabel.innerHTML = '<span class="badge bg-success">Validé</span>';
                    } else {
                        validationLabel.innerHTML = '<span class="badge bg-secondary">Non-validé</span>';
                    }
                } else {
                    // Revert
                    this.checked = !this.checked;
                    alert('Erreur lors de la mise à jour');
                }
            } catch (error) {
                console.error('Error toggling validation:', error);
                this.checked = !this.checked;
                alert('Erreur lors de la mise à jour');
            }
        });
    }
});
