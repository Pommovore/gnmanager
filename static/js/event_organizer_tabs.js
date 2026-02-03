/**
 * event_organizer_tabs.js
 * Extracted logic from event_organizer_tabs.html
 * Requires window.GN_CONTEXT to be defined with:
 * - eventId
 * - csrfToken
 * - baseUrl
 */

function copyToClipboard(text, element) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const originalTitle = element.title;
        element.title = "Copié !";
        const tooltip = bootstrap.Tooltip.getOrCreateInstance(element);
        tooltip.show();
        setTimeout(() => {
            element.title = originalTitle;
            tooltip.hide();
        }, 1000);
    }).catch(err => {
        console.error('Erreur de copie :', err);
    });
}

document.addEventListener('DOMContentLoaded', function () {
    // Check for context
    if (!window.GN_CONTEXT) {
        console.error('GN_CONTEXT is missing. Defaulting to empty values.');
        window.GN_CONTEXT = { eventId: '', csrfToken: '', baseUrl: '' };
    }

    const { eventId, csrfToken } = window.GN_CONTEXT;
    // BaseURL is already sanitized in the HTML script block before this file runs
    const baseUrl = window.GN_CONTEXT.baseUrl || '';

    // Init tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'))
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // URL patterns for dynamic routes
    const updatePafInlineUrl = `${baseUrl}/event/${eventId}/participant/{p_id}/update_paf_inline`;
    const regenerateSecretUrl = `${baseUrl}/event/${eventId}/regenerate_secret`;

    // Logic for Generalities Tab (Links & Secret)
    const linksContainer = document.getElementById('links-container');
    const addLinkBtn = document.getElementById('add-link-btn');

    if (addLinkBtn && linksContainer) {
        addLinkBtn.addEventListener('click', function () {
            const row = document.createElement('div');
            row.className = 'row mb-2 link-row';
            row.innerHTML = `
            <div class="col-md-5">
                <input type="text" class="form-control form-control-sm" name="link_urls[]" placeholder="URL (https://...)" value="">
            </div>
            <div class="col-md-5">
                <input type="text" class="form-control form-control-sm" name="link_titles[]" placeholder="Titre (ex: Site Web)" value="">
            </div>
            <div class="col-md-2">
                <button type="button" class="btn btn-sm btn-outline-danger w-100 remove-link-btn"><i class="bi bi-trash"></i></button>
            </div>
        `;
            linksContainer.appendChild(row);
            attachRemoveLinkListeners();
        });
    }

    function attachRemoveLinkListeners() {
        document.querySelectorAll('.remove-link-btn').forEach(btn => {
            btn.onclick = function () {
                this.closest('.link-row').remove();
            };
        });
    }
    attachRemoveLinkListeners();

    // --- P.A.F. Filter & Stats Logic ---
    const pafTypeFilter = document.getElementById('pafTypeFilter');
    const pafRows = document.querySelectorAll('.paf-participant-row');
    const pafCountEl = document.getElementById('pafCount');
    const pafTotalPaidEl = document.getElementById('pafTotalPaidDisplay');
    const pafTotalMissingEl = document.getElementById('pafTotalMissingDisplay');

    function updatePafStats() {
        let count = 0;
        let totalPaid = 0;
        let totalMissing = 0;

        pafRows.forEach(row => {
            if (row.style.display !== 'none') {
                count++;
                const paid = parseFloat(row.dataset.pafPaid) || 0;
                const remaining = parseFloat(row.dataset.pafRemaining) || 0;

                totalPaid += paid;
                if (remaining > 0) {
                    totalMissing += remaining;
                }
            }
        });

        if (pafCountEl) pafCountEl.textContent = count;
        if (pafTotalPaidEl) pafTotalPaidEl.textContent = totalPaid.toFixed(2) + ' €';
        if (pafTotalMissingEl) pafTotalMissingEl.textContent = totalMissing.toFixed(2) + ' €';
    }

    const pafStatusFilter = document.getElementById('pafStatusFilter');

    function applyPafFilters() {
        const typeValue = pafTypeFilter ? pafTypeFilter.value : 'all';
        const statusValue = pafStatusFilter ? pafStatusFilter.value : 'all';

        pafRows.forEach(row => {
            const rowType = row.dataset.pafType;
            const rowStatus = (row.dataset.pafStatus || '').toLowerCase();

            const typeMatch = (typeValue === 'all' || rowType === typeValue);
            const statusMatch = (statusValue === 'all' || rowStatus === statusValue);

            if (typeMatch && statusMatch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
        updatePafStats();
    }

    if (pafTypeFilter) {
        pafTypeFilter.addEventListener('change', applyPafFilters);
    }
    if (pafStatusFilter) {
        pafStatusFilter.addEventListener('change', applyPafFilters);
    }

    // Initial calc
    updatePafStats();

    const regenerateBtn = document.getElementById('regenerate-secret-btn');
    if (regenerateBtn) {
        regenerateBtn.addEventListener('click', function () {
            if (confirm('Êtes-vous sûr de vouloir régénérer la clé API ? L\'ancienne clé ne fonctionnera plus immédiatement.')) {
                fetch(regenerateSecretUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json'
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const valEl = document.getElementById('webhook-secret-value');
                            valEl.textContent = data.new_secret;
                            valEl.classList.add('text-success', 'fw-bold');
                            setTimeout(() => valEl.classList.remove('text-success', 'fw-bold'), 2000);
                        } else {
                            alert('Erreur lors de la régénération.');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Une erreur est survenue.');
                    });
            }
        });
    }

    // Dynamic PAF Configuration Rows
    const pafConfigContainer = document.getElementById('paf-config-container');
    const addPafBtn = document.getElementById('add-paf-btn');

    if (pafConfigContainer && addPafBtn) {
        addPafBtn.addEventListener('click', function () {
            const row = document.createElement('div');
            row.className = 'row mb-2 paf-row';
            row.innerHTML = `
            <div class="col-md-5">
                <input type="text" class="form-control form-control-sm" name="paf_names[]" placeholder="Nom (ex: PJ Standard)" value="">
            </div>
            <div class="col-md-5">
                <div class="input-group input-group-sm">
                    <input type="number" class="form-control" name="paf_amounts[]" placeholder="Montant" value="" step="0.01">
                    <span class="input-group-text">€</span>
                </div>
            </div>
            <div class="col-md-2">
                 <button type="button" class="btn btn-sm btn-outline-danger w-100 remove-paf-btn"><i class="bi bi-trash"></i></button>
            </div>
        `;
            pafConfigContainer.appendChild(row);
        });

        pafConfigContainer.addEventListener('click', function (e) {
            if (e.target.closest('.remove-paf-btn')) {
                e.target.closest('.paf-row').remove();
            }
        });
    }

    // AJAX updates for PAF Inline Editing
    document.querySelectorAll('.paf-inline-edit').forEach(el => {
        el.addEventListener('change', function () {
            const pId = this.dataset.pId;
            const field = this.dataset.field;
            const value = this.value;
            updateParticipantPAF(pId, { [field]: value });
        });
    });

    function updateParticipantPAF(pId, data) {
        fetch(updatePafInlineUrl.replace('{p_id}', pId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // Update Status Badge
                    const badge = document.querySelector(`.paf-status-badge[data-p-id="${pId}"]`);
                    if (badge) {
                        badge.textContent = result.paf_status_cap;
                        badge.className = 'badge paf-status-badge';
                        if (result.paf_status === 'versée') badge.classList.add('bg-success');
                        else if (result.paf_status === 'partielle') badge.classList.add('bg-warning', 'text-dark');
                        else badge.classList.add('bg-danger');
                    }

                    // Update Due Amount
                    const dueEl = document.querySelector(`.paf-due-amount[data-p-id="${pId}"]`);
                    if (dueEl) dueEl.textContent = `${result.due.toFixed(2)} €`;

                    // Update Payment Amount Display
                    const amountDisplay = document.querySelector(`.paf-payment-amount-display[data-p-id="${pId}"]`);
                    if (amountDisplay) amountDisplay.textContent = `${result.payment_amount.toFixed(2)} €`;

                    // Update edit button data-amount if exists
                    const amountBtn = document.querySelector(`.paf-edit-amount-btn[data-p-id="${pId}"]`);
                    if (amountBtn) amountBtn.dataset.amount = result.payment_amount;

                    // Update Remaining Amount
                    const remainingContainer = document.querySelector(`.paf-remaining-container[data-p-id="${pId}"]`);
                    if (remainingContainer) {
                        const rem = result.remaining;
                        if (rem > 0.01) {
                            remainingContainer.innerHTML = `<span class="text-danger fw-bold">${rem.toFixed(2)} €</span>`;
                        } else if (rem < -0.01) {
                            remainingContainer.innerHTML = `<span class="text-success">${rem.toFixed(2)} € (Trop perçu)</span>`;
                        } else {
                            remainingContainer.innerHTML = `<span class="text-success"><i class="bi bi-check-lg"></i> Payé</span>`;
                        }
                    }

                    // Update Info Button Color and Title
                    const infoBtn = document.querySelector(`.paf-info-btn[data-p-id="${pId}"]`);
                    if (infoBtn) {
                        if (result.info_payement_empty) {
                            infoBtn.classList.remove('btn-outline-danger');
                            infoBtn.classList.add('btn-outline-primary');
                            infoBtn.title = 'Aucune information';
                            infoBtn.dataset.info = '';
                        } else {
                            infoBtn.classList.remove('btn-outline-primary');
                            infoBtn.classList.add('btn-outline-danger');
                            infoBtn.title = result.info_payement;
                            infoBtn.dataset.info = result.info_payement;
                        }
                        // Re-init tooltip
                        const tooltip = bootstrap.Tooltip.getInstance(infoBtn);
                        if (tooltip) tooltip.setContent({ '.tooltip-inner': infoBtn.title });
                    }

                    // Update Global Comment Button Color and Title
                    const gcBtn = document.querySelector(`.paf-global-comment-btn[data-p-id="${pId}"]`);
                    if (gcBtn) {
                        if (result.global_comment_empty) {
                            gcBtn.classList.remove('btn-outline-danger');
                            gcBtn.classList.add('btn-outline-primary');
                            gcBtn.title = 'Aucun commentaire général';
                            gcBtn.dataset.comment = '';
                        } else {
                            gcBtn.classList.remove('btn-outline-primary');
                            gcBtn.classList.add('btn-outline-danger');
                            gcBtn.title = result.global_comment;
                            gcBtn.dataset.comment = result.global_comment;
                        }
                        const tooltip = bootstrap.Tooltip.getInstance(gcBtn);
                        if (tooltip) tooltip.setContent({ '.tooltip-inner': gcBtn.title });
                    }
                } else {
                    console.error('Update failed:', result.error);
                }
            })
            .catch(error => console.error('Fetch error:', error));
    }

    // Info Payment Modal Logic
    const infoModalEl = document.getElementById('infoPayementModal');
    let infoModal = null;
    if (infoModalEl) {
        infoModal = new bootstrap.Modal(infoModalEl);
    }
    let currentPId = null;

    document.querySelectorAll('.paf-info-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentPId = this.dataset.pId;
            document.getElementById('infoPayementParticipant').textContent = this.dataset.pName;
            document.getElementById('infoPayementTextarea').value = this.dataset.info || '';
            if (infoModal) infoModal.show();
        });
    });

    const saveInfoBtn = document.getElementById('saveInfoPayementBtn');
    if (saveInfoBtn) {
        saveInfoBtn.addEventListener('click', function () {
            const text = document.getElementById('infoPayementTextarea').value;
            updateParticipantPAF(currentPId, { info_payement: text });
            if (infoModal) infoModal.hide();
        });
    }

    // Global Comment Modal Logic
    const gcModalEl = document.getElementById('globalCommentModal');
    let gcModal = null;
    if (gcModalEl) {
        gcModal = new bootstrap.Modal(gcModalEl);
    }

    document.querySelectorAll('.paf-global-comment-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentPId = this.dataset.pId;
            document.getElementById('globalCommentParticipant').textContent = this.dataset.pName;
            document.getElementById('globalCommentTextarea').value = this.dataset.comment || '';
            if (gcModal) gcModal.show();
        });
    });

    const saveGcBtn = document.getElementById('saveGlobalCommentBtn');
    if (saveGcBtn) {
        saveGcBtn.addEventListener('click', function () {
            const text = document.getElementById('globalCommentTextarea').value;
            updateParticipantPAF(currentPId, { global_comment: text });
            if (gcModal) gcModal.hide();
        });
    }

    // Payment Amount Modal Logic
    const amountModalEl = document.getElementById('paymentAmountModal');
    let amountModal = null;
    if (amountModalEl) {
        amountModal = new bootstrap.Modal(amountModalEl);
    }

    document.querySelectorAll('.paf-edit-amount-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentPId = this.dataset.pId;
            document.getElementById('paymentAmountParticipant').textContent = this.dataset.pName;
            document.getElementById('paymentAmountInput').value = this.dataset.amount;
            if (amountModal) amountModal.show();
        });
    });

    const saveAmountBtn = document.getElementById('savePaymentAmountBtn');
    if (saveAmountBtn) {
        saveAmountBtn.addEventListener('click', function () {
            const amount = document.getElementById('paymentAmountInput').value;
            updateParticipantPAF(currentPId, { payment_amount: parseFloat(amount) });
            if (amountModal) amountModal.hide();
        });
    }

});
