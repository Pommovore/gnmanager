/**
 * Utility functions for GN Manager
 */

/**
 * Copie du texte dans le presse-papier et affiche une notification visuelle
 * @param {string} text - Le texte à copier
 * @param {HTMLElement} iconElement - L'élément icône qui a été cliqué (pour l'animation)
 */
function copyToClipboard(text, iconElement) {
    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
        // Animation visuelle de succès
        if (iconElement) {
            const originalClass = iconElement.className;
            iconElement.classList.add('text-success');
            iconElement.style.transform = 'scale(1.3)';

            setTimeout(() => {
                iconElement.className = originalClass;
                iconElement.style.transform = 'scale(1)';
            }, 500);
        }

        // Optionnel: Afficher une toast notification si Bootstrap Toast est disponible
        showToast('Copié dans le presse-papier', 'success');
    }).catch(err => {
        console.error('Erreur lors de la copie:', err);
        showToast('Erreur lors de la copie', 'danger');
    });
}

/**
 * Affiche une notification toast (si disponible)
 * @param {string} message - Le message à afficher
 * @param {string} type - Le type de toast (success, danger, warning, info)
 */
function showToast(message, type = 'info') {
    // Simple fallback si pas de toast Bootstrap
    console.log(`[${type.toUpperCase()}] ${message}`);

    // TODO: Implémenter un vrai système de toast si nécessaire
    // Pour l'instant, on peut utiliser un simple alert ou console.log
}

/**
 * Initialise les event listeners pour les icônes de contact (copy to clipboard)
 */
function initContactIcons() {
    document.addEventListener('click', (e) => {
        const icon = e.target.closest('.contact-icon');
        if (!icon) return;

        const text = icon.getAttribute('data-copy-text');
        if (text && text !== 'Non renseigné ou privé') {
            copyToClipboard(text, icon);
        }
    });
}

/**
 * Lit le contexte GN depuis les data-attributes d'un conteneur
 * @param {string} selector - Selecteur CSS du conteneur (par défaut: body ou premier élément avec data-event-id)
 * @returns {Object} - Objet contenant eventId, csrfToken, baseUrl
 */
function getGNContext(selector = null) {
    let container;

    if (selector) {
        container = document.querySelector(selector);
    } else {
        // Chercher le premier élément avec data-event-id
        container = document.querySelector('[data-event-id]') || document.body;
    }

    const eventId = container.getAttribute('data-event-id') || '';
    const csrfToken = container.getAttribute('data-csrf-token') || '';
    let baseUrl = container.getAttribute('data-base-url') || '';

    // Sanitization logic for baseUrl
    if (baseUrl === '/') baseUrl = '';
    if (baseUrl.endsWith('/')) baseUrl = baseUrl.slice(0, -1);

    return {
        eventId,
        csrfToken,
        baseUrl
    };
}

// Initialiser au chargement du DOM
document.addEventListener('DOMContentLoaded', () => {
    initContactIcons();
});

// Export pour compatibilité (si modules ES6 utilisés plus tard)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { copyToClipboard, getGNContext, showToast };
}
