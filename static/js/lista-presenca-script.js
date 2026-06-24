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

function atualizarContador(delta) {
    const el = document.getElementById('contador-presentes');
    if (!el) return;
    const atual = parseInt(el.textContent, 10) || 0;
    el.textContent = Math.max(0, atual + delta);
}

document.querySelectorAll('.check-presenca').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const container = document.querySelector('.container-refeitorio');
        if (container && container.dataset.chamadaAberta !== '1') {
            this.checked = !this.checked;
            showToast('A chamada não está aberta para edição.', 'error');
            return;
        }

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
                row.classList.remove('status-pendente', 'status-presente', 'status-ausente', 'status-ativa', 'status-concluida');
                row.classList.add(checked ? 'status-presente' : 'status-pendente');

                const badge = row.querySelector('.badge-status');
                if (badge) {
                    badge.className = checked ? 'badge-status presente' : 'badge-status pendente';
                    badge.textContent = checked ? 'Presente' : 'Pendente';
                }

                atualizarContador(checked ? 1 : -1);
                return data;
            });
        })
        .catch(error => {
            console.error('Erro ao atualizar presença:', error);
            reverterCheckbox();
            showToast(error.message || 'Erro de conexão com o servidor.', 'error');
        })
        .finally(() => {
            if (container && container.dataset.chamadaAberta === '1') {
                this.disabled = false;
            }
            row.classList.remove('processando-presenca');
        });
    });
});

(function initModalEncerrar() {
    const btnEncerrar = document.getElementById('btn-encerrar-chamada');
    const modal = document.getElementById('modal-confirmar-encerrar');
    const formEncerrar = document.getElementById('form-encerrar-chamada');
    const btnCancelar = document.getElementById('btn-modal-cancelar');
    const btnConfirmar = document.getElementById('btn-modal-confirmar');
    const modalMensagem = document.getElementById('modal-mensagem');

    if (!btnEncerrar || !modal || !formEncerrar) return;

    btnEncerrar.addEventListener('click', function() {
        const pendentes = parseInt(this.dataset.pendentes, 10) || 0;
        if (pendentes === 0) {
            modalMensagem.textContent = 'Todos os alunos foram marcados como presentes. Deseja encerrar a chamada?';
        } else if (pendentes === 1) {
            modalMensagem.textContent = '1 aluno sem presença receberá 1 strike. Confirmar encerramento?';
        } else {
            modalMensagem.textContent = `${pendentes} alunos sem presença receberão 1 strike cada. Confirmar encerramento?`;
        }
        modal.classList.remove('hidden');
    });

    btnCancelar.addEventListener('click', () => modal.classList.add('hidden'));
    btnConfirmar.addEventListener('click', () => formEncerrar.submit());

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
})();
