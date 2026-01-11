document.addEventListener('DOMContentLoaded', function () {
    // Participants Pool
    const participantsPool = document.getElementById('participants-pool');
    Sortable.create(participantsPool, {
        group: {
            name: 'shared',
            pull: true,
            put: true
        },
        animation: 150,
        sort: false, // Don't sort inside the pool
        onAdd: function (evt) {
            // Logic when participant returns to pool (unassign)
            const item = evt.item;
            const participantId = item.getAttribute('data-participant-id');
            const eventId = item.getAttribute('data-event-id');

            // Call API to unassign
            fetch('/api/casting/unassign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    participant_id: participantId,
                    event_id: eventId
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        alert('Erreur lors de la désaffectation');
                        // Revert move
                    }
                });
        }
    });

    // Role Slots
    const roleSlots = document.querySelectorAll('.role-slot');
    roleSlots.forEach(slot => {
        Sortable.create(slot, {
            group: {
                name: 'shared',
                pull: true,
                put: function (to, from, item) {
                    // Only allow put if slot is empty
                    return to.el.children.length === 0;
                }
            },
            animation: 150,
            onAdd: function (evt) {
                const item = evt.item;
                const participantId = item.getAttribute('data-participant-id');
                const roleId = slot.getAttribute('data-role-id');
                const eventId = slot.getAttribute('data-event-id');

                // Call API to assign
                fetch('/api/casting/assign', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        participant_id: participantId,
                        role_id: roleId,
                        event_id: eventId
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (!data.success) {
                            alert('Erreur lors de l\'affectation');
                            // Revert move if possible
                        }
                    });
            }
        });
    });
});
