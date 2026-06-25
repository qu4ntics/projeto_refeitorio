function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="bi ${type === 'success' ? 'bi-check-circle' : 'bi-exclamation-triangle'}"></i> ${message}`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

document.querySelectorAll('.check-presenca').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const reservaId = this.getAttribute('data-reserva-id');
        const checked = this.checked;
        const row = this.closest('tr');
        const reverterCheckbox = () => {
            this.checked = !checked;
        };

        this.disabled = true;
        row.classList.add('processando-presenca');

        fetch(`/administrativo/refeitorio/atualizar-status-reserva/${reservaId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ checked })
        })
        .then(response => {
            return response.json().catch(() => {
                throw new Error('Resposta inválida do servidor.');
            }).then(data => {
                if (!response.ok) {
                    throw new Error(data.erro || 'Erro ao atualizar o status no banco de dados.');
                }

                showToast('Presença atualizada!');
                row.classList.remove('status-ativa', 'status-concluida');
                row.classList.add(checked ? 'status-concluida' : 'status-ativa');

                return data;
            });
        })
        .catch(error => {
            console.error('Erro ao atualizar presença:', error);
            reverterCheckbox();
            showToast(error.message || 'Erro de conexão com o servidor.', 'error');
        })
        .finally(() => {
            this.disabled = false;
            row.classList.remove('processando-presenca');
        });
    });
});
