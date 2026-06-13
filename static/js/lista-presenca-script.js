function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="bi ${type === 'success' ? 'bi-check-circle' : 'bi-exclamation-triangle'}"></i> ${message}`;
    
    container.appendChild(toast);

    // Remove o toast após 3 segundos com efeito de fade
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

        // Feedback Visual: Desabilita e sinaliza processamento
        this.disabled = true;
        row.classList.add('processando-presenca');

        fetch(`/administrativo/refeitorio/atualizar-status-reserva/${reservaId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ 'checked': checked })
        })
        .then(response => {
            if (response.ok) {
                showToast('Presença atualizada!');
                
                // Sincroniza a classe da linha com o novo estado para evitar "cor fantasma"
                row.classList.remove('status-ativa', 'status-concluida');
                row.classList.add(checked ? 'status-concluida' : 'status-ativa');
                
                return response.json();
            }
            
            return response.json().then(data => {
                // Feedback silencioso no console em caso de erro de negócio
                console.warn(data.erro || 'Erro ao atualizar o status no banco de dados.');
                showToast(data.erro || 'Erro na atualização', 'error');
                this.checked = !checked; // Reverte o checkbox
                throw new Error(data.erro);
            });
        })
        .catch(error => {
            console.error('Erro AJAX:', error);
            if (!row.classList.contains('status-cancelada')) {
                // Se não foi um erro de negócio (cancelada), avisa sobre conexão
                if (!error.message) showToast('Erro de conexão com o servidor', 'error');
            }
        })
        .finally(() => {
            // Remove sinalização e reabilita
            this.disabled = false;
            row.classList.remove('processando-presenca');
        });
    });
});