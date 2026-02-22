/**
 * Script pour la page admin_logs.html
 * 
 * Gère le bouton "Marquer tout comme vu" via data attributes.
 */

document.addEventListener('DOMContentLoaded', function () {
    const markViewedBtn = document.getElementById('markViewedBtn');

    if (markViewedBtn) {
        const url = markViewedBtn.getAttribute('data-url');
        const csrfToken = markViewedBtn.getAttribute('data-csrf');

        markViewedBtn.addEventListener('click', function () {
            if (confirm('Marquer tous les logs comme consultés ?')) {
                fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('Erreur:', error);
                        alert('Erreur lors de la mise à jour des logs');
                    });
            }
        });
    }
});
