/**
 * Event Modals - Dynamic Join Modal Behavior
 * Handles the join modal's different modes (normal inscription vs préinscription)
 */

document.addEventListener('DOMContentLoaded', function () {
    // Gestion dynamique du modal d'inscription
    var joinModal = document.getElementById('joinModal');
    if (joinModal) {
        joinModal.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            var mode = button.getAttribute('data-mode');
            var helpMsg = document.getElementById('joinHelpWithMessage');
            var commentLabel = document.getElementById('commentLabel');
            var submitBtn = joinModal.querySelector('button[type="submit"]');

            var modalActionType = document.getElementById('modalActionType');

            if (mode === 'interest') {
                helpMsg.classList.remove('d-none');
                commentLabel.textContent = "Votre message :";
                if (modalActionType) modalActionType.textContent = "Préinscription";
            } else {
                helpMsg.classList.add('d-none');
                commentLabel.textContent = "Une précision ?";
                if (modalActionType) modalActionType.textContent = "Inscription";
            }
        });
    }
});
