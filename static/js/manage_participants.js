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
});
