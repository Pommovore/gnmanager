/**
 * Dashboard page JavaScript
 * Gère les tooltips et l'initialisation des images de fond des cartes événements.
 */

document.addEventListener('DOMContentLoaded', function () {
    // Initialiser tous les tooltips Bootstrap sur la page
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // --- Initialisation des images de fond des cartes événements ---
    const cards = document.querySelectorAll('.event-card[data-bg]');
    cards.forEach(function (card) {
        const bgUrl = card.getAttribute('data-bg');
        const bgDiv = card.querySelector('.event-card-bg');
        if (bgDiv && bgUrl) {
            bgDiv.style.backgroundImage = 'url("' + bgUrl + '")';
        }
    });
});
