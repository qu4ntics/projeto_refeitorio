document.querySelectorAll('.check-presenca').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const reservaId = this.getAttribute('data-reserva-id');
        const checked = this.checked;

        fetch(`/refeitorio/atualizar-status-reserva/${reservaId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': '{{ csrf_token }}'
            },
            body: JSON.stringify({ 'checked': checked })
        })
        .then(response => {
            if (!response.ok) {
                alert('Erro ao atualizar o status no banco de dados.');
                this.checked = !checked; // Desfaz a marcação visual se der erro no servidor
            }
        });
    });
});