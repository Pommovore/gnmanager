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
    const tableRows = document.querySelectorAll('#participants-table tbody tr');

    function applyFilters() {
        const typeVal = filterType ? filterType.value : '';
        const genreVal = filterGenre ? filterGenre.value : '';
        const statusVal = filterStatus ? filterStatus.value : '';
        const pafVal = filterPaf ? filterPaf.value : '';

        tableRows.forEach(row => {
            const rType = row.dataset.type || '';
            const rGenre = row.dataset.genre || '';
            const rStatus = row.dataset.status || '';
            const rPaf = row.dataset.paf || '';

            let show = true;
            if (typeVal && rType !== typeVal) show = false;
            if (genreVal && rGenre !== genreVal) show = false;
            if (statusVal && rStatus !== statusVal) show = false;
            if (pafVal && rPaf !== pafVal) show = false;

            row.style.display = show ? '' : 'none';
        });
    }

    if (filterType) filterType.addEventListener('change', applyFilters);
    if (filterGenre) filterGenre.addEventListener('change', applyFilters);
    if (filterStatus) filterStatus.addEventListener('change', applyFilters);
    if (filterPaf) filterPaf.addEventListener('change', applyFilters);

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
});
