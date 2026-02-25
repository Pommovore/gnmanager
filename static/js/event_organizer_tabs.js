/**
 * event_organizer_tabs.js
 * Extracted logic from event_organizer_tabs.html
 * Reads context from #event-context-data data-* attributes:
 * - data-event-id
 * - data-csrf-token
 * - data-base-url
 * - data-regenerate-url
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
    let context = window.GN_CONTEXT;

    // Fallback: Check for data attribute implementation
    if (!context) {
        const dataEl = document.getElementById('event-context-data');
        if (dataEl) {
            context = {
                eventId: dataEl.dataset.eventId,
                csrfToken: dataEl.dataset.csrfToken,
                baseUrl: dataEl.dataset.baseUrl,
                regenerateUrl: dataEl.dataset.regenerateUrl
            };
            // Sanitization: Ensure eventId is used correctly if it ends up being a string
        }
    }

    if (!context || !context.eventId) {
        console.error('GN_CONTEXT is missing or incomplete.');
        alert("Erreur technique: L'identifiant de l'événement est manquant. Veuillez rafraîchir la page.");
        // Prevent crashes by defaulting but logging error
        context = { eventId: '', csrfToken: '', baseUrl: '' };
    }

    const { eventId, csrfToken } = context;
    // Sanitize baseUrl to avoid "//path" which browser interprets as protocol-relative
    const baseUrl = (context.baseUrl || '').replace(/\/$/, '');

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
                // Use the explicit URL from context to avoid any ambiguity
                const finalRegenerateUrl = context.regenerateUrl;

                if (!finalRegenerateUrl) {
                    alert('Erreur technique: L\'URL de régénération est manquante. Veuillez rafraîchir la page (CTRL+F5).');
                    console.error('Missing regenerateUrl in context', context);
                    return;
                }

                fetch(finalRegenerateUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': context.csrfToken,
                        'Content-Type': 'application/json'
                    }
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data.success) {
                            const valEl = document.getElementById('webhook-secret-value');
                            if (valEl) {
                                valEl.textContent = data.new_secret;
                                valEl.classList.add('text-success', 'fw-bold');
                                setTimeout(() => valEl.classList.remove('text-success', 'fw-bold'), 2000);
                            } else {
                                console.warn("Element 'webhook-secret-value' not found to update.");
                            }
                        } else {
                            alert('Erreur lors de la régénération: ' + (data.error || 'Erreur inconnue'));
                        }
                    })
                    .catch(error => {
                        console.error('Error regenerating secret:', error);
                        alert('Une erreur est survenue lors de la communication avec le serveur.');
                    });
            }
        });
    }

    // Copy Secret Button Logic
    const copySecretBtn = document.getElementById('copy-secret-btn');
    if (copySecretBtn) {
        copySecretBtn.addEventListener('click', function () {
            const secretVal = document.getElementById('webhook-secret-value');
            if (secretVal) {
                // Ensure text is trimmed to avoid copying surrounding whitespace
                copyToClipboard(secretVal.textContent.trim(), this);
            }
        });
    }

    // Copy Event URL Button Logic
    const copyEventUrlBtn = document.getElementById('copy-event-url-btn');
    if (copyEventUrlBtn) {
        copyEventUrlBtn.addEventListener('click', function () {
            const urlInput = document.getElementById('event-url-input');
            if (urlInput) {
                copyToClipboard(urlInput.value, this);
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

                    // Update Payment Amount Input
                    const amountInput = document.querySelector(`.paf-inline-edit-amount[data-p-id="${pId}"]`);
                    if (amountInput) {
                        amountInput.value = result.payment_amount.toFixed(2);
                        amountInput.classList.remove('border-warning');
                        amountInput.classList.add('border-success');
                        setTimeout(() => amountInput.classList.remove('border-success'), 2000);
                    }

                    // Update Payment Amount Display (Legacy/Fallback if element exists)
                    const amountDisplay = document.querySelector(`.paf-payment-amount-display[data-p-id="${pId}"]`);
                    if (amountDisplay) amountDisplay.textContent = `${result.payment_amount.toFixed(2)} €`;

                    // Update edit button data-amount if exists
                    const amountBtn = document.querySelector(`.paf-edit-amount-btn[data-p-id="${pId}"]`);
                    if (amountBtn) amountBtn.dataset.amount = result.payment_amount;

                    // Update Remaining Amount
                    const remainingContainer = document.querySelector(`.paf-remaining-container[data-p-id="${pId}"]`);
                    if (remainingContainer) {
                        if (!result.paf_type) {
                            remainingContainer.innerHTML = `<span class="text-muted fs-4">?</span>`;
                        } else {
                            const rem = result.remaining;
                            if (rem > 0.01) {
                                remainingContainer.innerHTML = `<span class="text-danger fw-bold">${rem.toFixed(2)} €</span>`;
                            } else if (rem < -0.01) {
                                remainingContainer.innerHTML = `<span class="text-success">${rem.toFixed(2)} € (Trop perçu)</span>`;
                            } else {
                                remainingContainer.innerHTML = `<span class="text-success"><i class="bi bi-check-lg"></i> Payé</span>`;
                            }
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

                    // Update datasets for recalculation of stats
                    const pafRow = document.querySelector(`.paf-participant-row[data-p-id="${pId}"]`) ||
                        document.querySelector(`[data-p-id="${pId}"]`)?.closest('.paf-participant-row');
                    if (pafRow) {
                        pafRow.dataset.pafPaid = result.payment_amount || 0;
                        pafRow.dataset.pafRemaining = result.remaining || 0;
                    }

                    // Recalculate global PAF stats
                    if (typeof updatePafStats === 'function') {
                        updatePafStats();
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

    // Payment Amount Modal Logic (Deprecated but code kept for reference if needed, button removed)
    const amountModalEl = document.getElementById('paymentAmountModal');
    let amountModal = null;
    if (amountModalEl) {
        amountModal = new bootstrap.Modal(amountModalEl);
    }

    // Inline Amount Edit Logic (Enter key to save)
    document.querySelectorAll('.paf-inline-edit-amount').forEach(input => {
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // Prevent form submission if inside one
                const pId = this.dataset.pId;
                const amount = parseFloat(this.value);

                if (isNaN(amount)) {
                    alert("Veuillez entrer un montant valide.");
                    return;
                }

                // Blur to indicate action is being processed
                this.blur();

                // Show loading state (optional, maybe change border color?)
                this.classList.add('border-warning');

                updateParticipantPAF(pId, { payment_amount: amount });
            }
        });

        // Auto-select content on focus for easier editing
        input.addEventListener('focus', function () {
            this.select();
        });
    });

    /* 
    document.querySelectorAll('.paf-edit-amount-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentPId = this.dataset.pId;
            document.getElementById('paymentAmountParticipant').textContent = this.dataset.pName;
            document.getElementById('paymentAmountInput').value = this.dataset.amount;
            if (amountModal) amountModal.show();
        });
    });
    */

    const saveAmountBtn = document.getElementById('savePaymentAmountBtn');
    if (saveAmountBtn) {
        saveAmountBtn.addEventListener('click', function () {
            const amount = document.getElementById('paymentAmountInput').value;
            updateParticipantPAF(currentPId, { payment_amount: parseFloat(amount) });
            if (amountModal) amountModal.hide();
        });
    }

    // --- Notification Mark as Read functionality ---
    function updateNotificationBadge() {
        const unreadCount = document.querySelectorAll('.notification-unread').length;
        const bellIcon = document.querySelector('#list-notifications-list i.bi-bell');
        if (bellIcon) {
            if (unreadCount > 0) {
                bellIcon.classList.add('text-danger');
                bellIcon.style.setProperty('color', '#d35400', 'important');
            } else {
                bellIcon.classList.remove('text-danger');
                bellIcon.style.color = '';
            }
        }
    }

    document.querySelectorAll('.mark-read-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const notifId = this.dataset.notifId;

            fetch(`${baseUrl}/event/${eventId}/notification/${notifId}/mark_read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Remove highlight and button
                        const item = this.closest('.list-group-item');
                        item.classList.remove('notification-unread');
                        this.remove();
                        updateNotificationBadge();
                    }
                })
                .catch(error => console.error('Error marking notification as read:', error));
        });
    });

    const markAllReadBtn = document.getElementById('mark-all-read-btn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function () {
            if (!confirm('Voulez-vous marquer toutes les notifications comme lues ?')) return;

            fetch(`${baseUrl}/event/${eventId}/notifications/mark_all_read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.querySelectorAll('.notification-unread').forEach(item => {
                            item.classList.remove('notification-unread');
                            const btn = item.querySelector('.mark-read-btn');
                            if (btn) btn.remove();
                        });
                        markAllReadBtn.remove();
                        updateNotificationBadge();
                    }
                })
                .catch(error => console.error('Error marking all notifications as read:', error));
        });
    }

    // --- Trombinoscope Refresh Logic ---
    const trombiTabLink = document.getElementById('list-trombinoscope-list');
    const trombiTabContent = document.getElementById('list-trombinoscope');

    if (trombiTabLink && trombiTabContent) {
        trombiTabLink.addEventListener('shown.bs.tab', function (e) {
            // Show spinner
            trombiTabContent.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Chargement...</span>
                    </div>
                    <p class="mt-2 text-muted">Chargement du trombinoscope...</p>
                </div>
            `;

            fetch(`${baseUrl}/event/${eventId}/trombinoscope_content`)
                .then(response => {
                    if (!response.ok) throw new Error('Erreur réseau');
                    return response.text();
                })
                .then(html => {
                    trombiTabContent.innerHTML = html;
                    // Re-init tooltips
                    const tooltips = trombiTabContent.querySelectorAll('[data-bs-toggle="tooltip"]');
                    tooltips.forEach(t => new bootstrap.Tooltip(t));

                    // Re-attach layout listeners
                    attachTrombiLayoutListeners();
                })
                .catch(error => {
                    console.error('Error loading trombinoscope:', error);
                    trombiTabContent.innerHTML = `
                        <div class="alert alert-danger m-3">
                            <i class="bi bi-exclamation-triangle"></i> Erreur lors du chargement du trombinoscope.
                        </div>
                    `;
                });
        });
    }

    // Helper to attach layout listeners (since content is replaced)
    function attachTrombiLayoutListeners() {
        const layoutButtons = document.querySelectorAll('.btn-group[aria-label="Layout Options"] button');
        const trombiContainer = document.querySelector('.trombi-container');

        if (layoutButtons.length > 0 && trombiContainer) {
            layoutButtons.forEach(btn => {
                // Remove old listeners to avoid duplicates? 
                // cloneNode(true) is a nuclear option, but simple addEventListener appends.
                // Since we replace innerHTML of tab, the buttons are new elements every time.
                // So no need to remove old listeners.

                btn.addEventListener('click', function () {
                    const layout = this.dataset.layout;

                    // Remove active class from all buttons
                    layoutButtons.forEach(b => b.classList.remove('active'));
                    // Add active class to clicked button
                    this.classList.add('active');

                    // Remove all layout classes from container
                    trombiContainer.classList.remove('layout-1', 'layout-2', 'layout-4');

                    // Add new layout class (if not 1, which is default)
                    if (layout !== '1') {
                        trombiContainer.classList.add(`layout-${layout}`);
                    }
                });
            });
        }
    }

    // Initial attachment (in case we land directly on the tab, though content is loaded server-side initially for first render?)
    // Actually, if we use include in template, the initial render has the content.
    // If we switch tabs, we reload it. 
    // We should attach listeners on initial load too.
    attachTrombiLayoutListeners();

});
