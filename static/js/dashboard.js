/**
 * Dashboard page JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
    // Initialiser tous les tooltips Bootstrap sur la page
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
