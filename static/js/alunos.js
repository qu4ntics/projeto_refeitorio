const CORES_AVATAR = ['av-verde', 'av-roxo', 'av-azul', 'av-laranja', 'av-rosa', 'av-ciano'];

let todosAlunos = [];
let alunoParaDesbloquear = null;

document.addEventListener('DOMContentLoaded', () => {
  carregarAlunos();

  document.getElementById('input-busca').addEventListener('input', aplicarFiltros);
  document.getElementById('filtro-turma').addEventListener('change', aplicarFiltros);

  const btnBloqueados = document.getElementById('btn-somente-bloqueados');
  btnBloqueados.addEventListener('click', () => {
    const ativo = btnBloqueados.dataset.ativo === 'true';
    btnBloqueados.dataset.ativo = String(!ativo);
    btnBloqueados.classList.toggle('ativo', !ativo);
    aplicarFiltros();
  });

  document.getElementById('btn-cancelar-modal').addEventListener('click', fecharModal);
  document.getElementById('btn-confirmar-desbloqueio').addEventListener('click', confirmarDesbloqueio);

  document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) fecharModal();
  });
});

async function carregarAlunos() {
  mostrarEstado('loading');

  try {
    const res = await fetch('/administrativo/alunos/json/');
    if (!res.ok) throw new Error('Erro na requisição');
    const data = await res.json();
    todosAlunos = data.alunos;
    mostrarEstado(null);
    aplicarFiltros();
  } catch (err) {
    console.error(err);
    mostrarEstado('erro');
  }
}

function aplicarFiltros() {
  const busca        = document.getElementById('input-busca').value.toLowerCase().trim();
  const turma        = document.getElementById('filtro-turma').value;
  const soBloqueados = document.getElementById('btn-somente-bloqueados').dataset.ativo === 'true';

  const filtrados = todosAlunos.filter(a => {
    const matchBusca = !busca || a.nome_completo.toLowerCase().includes(busca) || a.email.toLowerCase().includes(busca);
    const matchTurma = !turma || a.turma_id === turma;
    const matchBloc  = !soBloqueados || a.bloqueado;
    return matchBusca && matchTurma && matchBloc;
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

  corpo.innerHTML = alunos.map((a, i) => {
    const iniciais   = iniciais2(a.nome_completo);
    const cor        = CORES_AVATAR[somarChars(a.nome_completo) % CORES_AVATAR.length];
    const strikeCls  = `strike-${Math.min(a.strikes_ativos, 2)}`;
    const statusHtml = renderStatus(a);
    const expiracao  = a.proximo_strike_expira_em
      ? `<span class="strike-expira">Expira ${formatarData(a.proximo_strike_expira_em)}</span>`
      : '';
    const btnDesbl   = a.bloqueado
      ? `<button class="btn-desbloquear" onclick="abrirModal('${a.id}', '${escapar(a.nome_completo)}')">
           <i class="fa-solid fa-lock-open"></i> Desbloquear
         </button>`
      : '<span style="color:var(--text-light);font-size:12px;">—</span>';

    return `
      <div class="tabela-linha">
        <div class="aluno-info">
          <div class="aluno-avatar ${cor}">${iniciais}</div>
          <span class="aluno-nome">${escapar(a.nome_completo)}</span>
        </div>
        <span class="email">${escapar(a.email)}</span>
        <span class="turma">${escapar(a.turma)}</span>
        <div class="strikes-info">
          <span class="strike-badge ${strikeCls}">${a.strikes_ativos}/2</span>
          ${expiracao}
        </div>
        <div>${statusHtml}</div>
        <div>${btnDesbl}</div>
      </div>
    `;
  }).join('');
}

function renderStatus(a) {
  if (a.bloqueado || a.strikes_ativos >= 2) {
    return '<span class="status-badge status-bloqueado"><i class="fa-solid fa-lock"></i> Bloqueado</span>';
  }
  if (a.strikes_ativos === 1) {
    return '<span class="status-badge status-alerta"><i class="fa-solid fa-triangle-exclamation"></i> Alerta</span>';
  }
  return '<span class="status-badge status-normal"><i class="fa-solid fa-circle-check"></i> Normal</span>';
}

function abrirModal(id, nome) {
  alunoParaDesbloquear = id;
  document.getElementById('modal-desc').textContent =
    `Deseja desbloquear ${nome}? O aluno voltará a ter acesso normalmente à plataforma.`;
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
  document.getElementById('estado-vazio').hidden   = tipo !== 'vazio';
  document.getElementById('estado-erro').hidden    = tipo !== 'erro';
  document.getElementById('tabela-wrapper').hidden = tipo === 'loading' || tipo === 'erro';
}

function mostrarToast(msg, tipo = 'success') {
  const toast = document.getElementById('toast');
  toast.className = `toast toast-${tipo}`;
  toast.innerHTML = `<i class="fa-solid fa-${tipo === 'success' ? 'circle-check' : 'circle-xmark'}"></i> ${msg}`;
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, 3500);
}

function iniciais2(nome) {
  const partes = nome.trim().split(' ').filter(Boolean);
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function somarChars(str) {
  return str.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
}

function formatarData(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('pt-BR');
}

function escapar(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function getCookie(name) {
  const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return v ? v.pop() : '';
}