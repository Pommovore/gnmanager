/**
 * Admin page JavaScript functionality
 * Handles modal auto-opening and delete confirmations
 */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-open user edit modal if open_edit parameter is present
    const urlParams = new URLSearchParams(window.location.search);
    const openEditUserId = urlParams.get('open_edit');

    if (openEditUserId) {
        const modalId = 'editUserModal' + openEditUserId;
        const modalEl = document.getElementById(modalId);
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    // Handle delete user form confirmations
    document.querySelectorAll('form[action*="admin_delete_user"]').forEach(form => {
        form.addEventListener('submit', function (e) {
            const confirmed = confirm(
                "Êtes-vous sûr de vouloir supprimer cet utilisateur ? " +
                "Cette action est irréversible et effacera toutes ses données."
            );

            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});
