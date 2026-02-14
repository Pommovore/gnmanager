/**
 * manage_participants.js
 * Extracted logic from manage_participants.html
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
    const baseUrl = window.GN_CONTEXT.baseUrl || '';

    // Init tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'))
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    const updatePafInlineUrl = `${baseUrl}/event/${eventId}/participant/{p_id}/update_paf_inline`;

    // Global Comment Modal Logic
    const gcModalEl = document.getElementById('globalCommentModal');
    let gcModal = null;
    if (gcModalEl) {
        gcModal = new bootstrap.Modal(gcModalEl);
    }

    let currentPId = null;

    document.querySelectorAll('.gc-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            currentPId = this.dataset.pId;
            document.getElementById('globalCommentParticipant').textContent = this.dataset.pName;
            document.getElementById('globalCommentTextarea').value = this.title === 'Aucun commentaire général' ? '' : this.title;
            if (gcModal) gcModal.show();
        });
    });

    const saveGcBtn = document.getElementById('saveGlobalCommentBtn');
    if (saveGcBtn) {
        saveGcBtn.addEventListener('click', function () {
            const text = document.getElementById('globalCommentTextarea').value;

            fetch(updatePafInlineUrl.replace('{p_id}', currentPId), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ global_comment: text })
            })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        const gcBtn = document.querySelector(`.gc-btn[data-p-id="${currentPId}"]`);
                        if (gcBtn) {
                            if (result.global_comment_empty) {
                                gcBtn.classList.remove('btn-outline-danger');
                                gcBtn.classList.add('btn-outline-primary');
                                gcBtn.title = 'Aucun commentaire général';
                            } else {
                                gcBtn.classList.remove('btn-outline-primary');
                                gcBtn.classList.add('btn-outline-danger');
                                gcBtn.title = result.global_comment;
                            }
                        }
                        if (gcModal) gcModal.hide();
                    } else {
                        alert('Erreur: ' + (result.error || 'Inconnue'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Une erreur est survenue.');
                });
        });
    }

    // --- Filtering Logic ---
    const filterType = document.getElementById('participant-filter-type');
    const filterGenre = document.getElementById('participant-filter-genre');
    const filterStatus = document.getElementById('participant-filter-status');
    const filterPaf = document.getElementById('participant-filter-paf');
    const filterPhoto = document.getElementById('participant-filter-photo');
    const tableRows = document.querySelectorAll('#participants-table tbody tr');

    function applyFilters() {
        const typeVal = filterType ? filterType.value : '';
        const genreVal = filterGenre ? filterGenre.value : '';
        const statusVal = filterStatus ? filterStatus.value : '';
        const pafVal = filterPaf ? filterPaf.value : '';
        const photoVal = filterPhoto ? filterPhoto.value : '';

        tableRows.forEach(row => {
            const rType = row.dataset.type || '';
            const rGenre = row.dataset.genre || '';
            const rStatus = row.dataset.status || '';
            const rPaf = row.dataset.paf || '';
            const rPhoto = row.dataset.photo || '';

            let show = true;
            if (typeVal && rType !== typeVal) show = false;
            if (genreVal && rGenre !== genreVal) show = false;
            if (statusVal && rStatus !== statusVal) show = false;
            if (pafVal && rPaf !== pafVal) show = false;
            if (photoVal && rPhoto !== photoVal) show = false;

            row.style.display = show ? '' : 'none';
        });
    }

    if (filterType) filterType.addEventListener('change', applyFilters);
    if (filterGenre) filterGenre.addEventListener('change', applyFilters);
    if (filterStatus) filterStatus.addEventListener('change', applyFilters);
    if (filterPaf) filterPaf.addEventListener('change', applyFilters);
    if (filterPhoto) filterPhoto.addEventListener('change', applyFilters);

    // --- Sorting Logic ---
    const sortBtns = document.querySelectorAll('.participant-sort-btn');
    const tableBody = document.querySelector('#participants-table tbody');

    sortBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const sortKey = this.dataset.sort;
            console.log('Sorting by:', sortKey); // Debug

            // Get current direction (toggle it)
            // We use 'asc' as default if not set, so first click becomes 'asc' (if coming from nothing) or 'desc' depending on implementation.
            // Let's standardise: default state -> click -> asc -> click -> desc
            let currentDir = this.dataset.dir || 'none';
            let newDir = currentDir === 'asc' ? 'desc' : 'asc';

            // Reset other buttons
            sortBtns.forEach(b => {
                b.dataset.dir = 'none';
                b.querySelector('i').className = 'bi bi-arrow-down-up';
            });

            // Update this button
            this.dataset.dir = newDir;
            const icon = this.querySelector('i');
            icon.className = newDir === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';

            // Sort rows
            const rows = Array.from(tableBody.querySelectorAll('tr'));

            rows.sort((a, b) => {
                let valA = a.dataset[`sort${sortKey.charAt(0).toUpperCase() + sortKey.slice(1)}`];
                let valB = b.dataset[`sort${sortKey.charAt(0).toUpperCase() + sortKey.slice(1)}`];

                // Handle potential missing values
                valA = valA ? valA.toLowerCase() : '';
                valB = valB ? valB.toLowerCase() : '';

                // Contact score is numeric
                if (sortKey === 'contact') {
                    valA = parseInt(valA) || 0;
                    valB = parseInt(valB) || 0;
                    return newDir === 'asc' ? valA - valB : valB - valA;
                }

                // Default string sort
                if (valA < valB) return newDir === 'asc' ? -1 : 1;
                if (valA > valB) return newDir === 'asc' ? 1 : -1;
                return 0;
            });

            // Re-append rows
            rows.forEach(row => tableBody.appendChild(row));
        });
    });

    // --- Email List Logic ---
    const btnEmailList = document.getElementById('btn-email-list');
    const emailListModalElement = document.getElementById('emailListModal');
    const emailListModal = emailListModalElement ? new bootstrap.Modal(emailListModalElement) : null;
    const emailListTextarea = document.getElementById('emailListTextarea');
    const copyEmailListBtn = document.getElementById('copyEmailListBtn');

    if (btnEmailList) {
        btnEmailList.addEventListener('click', function () {
            const visibleRows = document.querySelectorAll('#participants-table tbody tr:not([style*="display: none"])');
            let emailList = [];

            visibleRows.forEach(row => {
                // Get Name
                const nameDiv = row.querySelector('.d-flex.flex-column strong');
                const name = nameDiv ? nameDiv.textContent.trim() : 'Inconnu';

                // Get Email (hidden in title or data attribute of the envelope icon)
                const emailIcon = row.querySelector('.bi-envelope');
                const email = emailIcon ? emailIcon.dataset.copyText : '';

                if (email) {
                    emailList.push(`${name} <${email}>,`);
                }
            });

            if (emailListTextarea) emailListTextarea.value = emailList.join('\n');
            if (emailListModal) emailListModal.show();
        });
    }

    if (copyEmailListBtn) {
        copyEmailListBtn.addEventListener('click', function () {
            if (!emailListTextarea) return;
            emailListTextarea.select();
            navigator.clipboard.writeText(emailListTextarea.value).then(() => {
                const originalHtml = copyEmailListBtn.innerHTML;
                copyEmailListBtn.innerHTML = '<i class="bi bi-check"></i> Copié !';
                copyEmailListBtn.classList.remove('btn-primary');
                copyEmailListBtn.classList.add('btn-success');

                setTimeout(() => {
                    copyEmailListBtn.innerHTML = originalHtml;
                    copyEmailListBtn.classList.remove('btn-success');
                    copyEmailListBtn.classList.add('btn-primary');
                }, 2000);
            }).catch(err => {
                console.error('Erreur lors de la copie :', err);
                alert('Impossible de copier automatiquement.');
            });
        });
    }

    // --- Bulk Delete Logic ---
    const btnDeleteFiltered = document.getElementById('btn-delete-filtered');

    if (btnDeleteFiltered) {
        btnDeleteFiltered.addEventListener('click', function () {
            const visibleRows = document.querySelectorAll('#participants-table tbody tr:not([style*="display: none"])');
            const participantIds = [];
            const names = [];

            visibleRows.forEach(row => {
                const pId = row.dataset.pId;
                if (pId) {
                    participantIds.push(parseInt(pId));
                    const nameEl = row.querySelector('.d-flex.flex-column strong');
                    if (nameEl) names.push(nameEl.textContent.trim());
                }
            });

            if (participantIds.length === 0) {
                alert('Aucun participant affiché à supprimer.');
                return;
            }

            const preview = names.slice(0, 10).join('\n• ');
            const extra = names.length > 10 ? `\n... et ${names.length - 10} autre(s)` : '';

            if (!confirm(`⚠️ Supprimer ${participantIds.length} participant(s) de la liste filtrée ?\n\n• ${preview}${extra}\n\nLes organisateurs ne seront PAS supprimés.\nCette action est irréversible !`)) {
                return;
            }

            btnDeleteFiltered.disabled = true;
            btnDeleteFiltered.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

            const eventId = window.location.pathname.match(/\/event\/(\d+)\//)?.[1];
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = csrfMeta ? csrfMeta.content : '';

            fetch(`${window.location.pathname.split('/participants')[0]}/participants/bulk-delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ participant_ids: participantIds })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        let msg = `${data.deleted} participant(s) supprimé(s).`;
                        if (data.skipped_orga > 0) {
                            msg += `\n\n⚠️ ${data.warning}`;
                        }
                        alert(msg);
                        window.location.reload();
                    } else {
                        alert('Erreur : ' + (data.error || 'Erreur inconnue'));
                    }
                })
                .catch(err => {
                    console.error('Error deleting participants:', err);
                    alert('Erreur technique lors de la suppression.');
                })
                .finally(() => {
                    btnDeleteFiltered.disabled = false;
                    btnDeleteFiltered.innerHTML = '<i class="bi bi-trash"></i> Supprimer';
                });
        });
    }
});
