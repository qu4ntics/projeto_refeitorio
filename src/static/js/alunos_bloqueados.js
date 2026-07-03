const CORES_AVATAR = ['av-verde', 'av-roxo', 'av-azul', 'av-laranja', 'av-rosa', 'av-ciano'];

let todosAlunos = [];
let alunoParaDesbloquear = null;

document.addEventListener('DOMContentLoaded', () => {
  carregarAlunos();

  document.getElementById('input-busca').addEventListener('input', aplicarFiltros);

  document.getElementById('btn-cancelar-modal')?.addEventListener('click', fecharModal);
  document.getElementById('btn-confirmar-desbloqueio')?.addEventListener('click', confirmarDesbloqueio);
  document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) fecharModal();
  });
});

async function carregarAlunos() {
  mostrarEstado('loading');

  try {
    const res = await fetch('/administrativo/alunos/json/?bloqueados=true');
    if (!res.ok) throw new Error('Erro na requisição');
    const data = await res.json();

    todosAlunos = data.alunos || [];

    const sub = document.getElementById('subtitulo-bloqueados');
    if (sub) {
      const total = todosAlunos.length;
      sub.textContent = total === 0
        ? 'Nenhum aluno bloqueado no momento.'
        : `${total} aluno${total !== 1 ? 's' : ''} bloqueado${total !== 1 ? 's' : ''} no sistema.`;
    }

    mostrarEstado(null);
    aplicarFiltros();
  } catch (err) {
    console.error(err);
    mostrarEstado('erro');
  }
}

function aplicarFiltros() {
  const busca = document.getElementById('input-busca').value.toLowerCase().trim();

  const filtrados = todosAlunos.filter(a => {
    if (!busca) return true;
    return (
      a.nome_completo.toLowerCase().includes(busca) ||
      a.email.toLowerCase().includes(busca) ||
      (a.turma && a.turma.toLowerCase().includes(busca))
    );
  });

  renderizarTabela(filtrados);
}

function renderizarTabela(alunos) {
  const corpo = document.getElementById('tabela-body');

  if (alunos.length === 0) {
    mostrarEstado('vazio');
    document.getElementById('tabela-wrapper').hidden = true;
    corpo.innerHTML = '';
    return;
  }

  mostrarEstado(null);
  document.getElementById('tabela-wrapper').hidden = false;

  corpo.innerHTML = alunos.map(a => {
    const iniciais = extrairIniciais(a.nome_completo);
    const cor = CORES_AVATAR[somarChars(a.nome_completo) % CORES_AVATAR.length];
    const dataBloqueio = a.bloqueado_em
      ? formatarDataHora(a.bloqueado_em)
      : '—';

    return `
      <div class="tabela-linha">
        <div class="aluno-info">
          <div class="aluno-avatar ${cor}">${iniciais}</div>
          <span class="aluno-nome">${escapar(a.nome_completo)}</span>
        </div>
        <span class="email">${escapar(a.email)}</span>
        <span class="turma-col">${escapar(a.turma) || '—'}</span>
        <span class="data-bloqueio">${dataBloqueio}</span>
        <div>
          <button class="btn-desbloquear"
            onclick="abrirModal('${escapar(a.id)}', '${escapar(a.nome_completo)}')">
            <i class="fa-solid fa-lock-open"></i> Desbloquear
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function abrirModal(id, nome) {
  alunoParaDesbloquear = id;
  document.getElementById('modal-desc').textContent =
    `Deseja desbloquear ${nome}? O aluno voltará a poder fazer novas reservas.`;
  document.getElementById('modal-overlay').hidden = false;
}

function fecharModal() {
  document.getElementById('modal-overlay').hidden = true;
  alunoParaDesbloquear = null;
}

async function confirmarDesbloqueio() {
  if (!alunoParaDesbloquear) return;

  const btn = document.getElementById('btn-confirmar-desbloqueio');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Aguarde...';

  try {
    const res = await fetch(`/administrativo/alunos/${alunoParaDesbloquear}/desbloquear/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    });
    if (!res.ok) throw new Error();

    fecharModal();
    await carregarAlunos();
    mostrarToast('Aluno desbloqueado com sucesso!', 'success');
  } catch {
    mostrarToast('Erro ao desbloquear. Tente novamente.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-lock-open"></i> Desbloquear';
  }
}

function mostrarEstado(tipo) {
  document.getElementById('estado-loading').hidden = tipo !== 'loading';
  document.getElementById('estado-vazio').hidden = tipo !== 'vazio';
  document.getElementById('estado-erro').hidden = tipo !== 'erro';
  const wrapper = document.getElementById('tabela-wrapper');
  if (tipo === 'loading' || tipo === 'erro' || tipo === 'vazio') wrapper.hidden = true;
}

function mostrarToast(msg, tipo = 'success') {
  const toast = document.getElementById('toast');
  toast.className = `toast toast-${tipo}`;
  toast.innerHTML = `<i class="fa-solid fa-${tipo === 'success' ? 'circle-check' : 'circle-xmark'}"></i> ${msg}`;
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, 3500);
}

function extrairIniciais(nome) {
  const partes = nome.trim().split(' ').filter(Boolean);
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function somarChars(str) {
  return str.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
}

function formatarDataHora(iso) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function escapar(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getCookie(name) {
  const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return v ? v.pop() : '';
}
