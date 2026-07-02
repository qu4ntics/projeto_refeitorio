const CORES_AVATAR = ['av-verde', 'av-roxo', 'av-azul', 'av-laranja', 'av-rosa', 'av-ciano'];

let todosAlunos = [];
let alunoParaDesbloquear = null;
let salvandoContraturno = false;
let timeoutContraturno = null;

document.addEventListener('DOMContentLoaded', () => {
  carregarAlunos();

  document.getElementById('input-busca').addEventListener('input', aplicarFiltros);

  const btnBloqueados = document.getElementById('btn-somente-bloqueados');
  btnBloqueados.addEventListener('click', () => {
    const ativo = btnBloqueados.dataset.ativo === 'true';
    btnBloqueados.dataset.ativo = String(!ativo);
    btnBloqueados.classList.toggle('ativo', !ativo);
    aplicarFiltros();
  });

  document.getElementById('btn-cancelar-modal')?.addEventListener('click', fecharModal);
  document.getElementById('btn-confirmar-desbloqueio')?.addEventListener('click', confirmarDesbloqueio);
  document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) fecharModal();
  });

  document.getElementById('btn-excluir-turma')?.addEventListener('click', abrirModalExcluir);
  document.getElementById('btn-cancelar-excluir')?.addEventListener('click', fecharModalExcluir);
  document.getElementById('btn-confirmar-excluir')?.addEventListener('click', confirmarExcluirTurma);
  document.getElementById('modal-excluir-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) fecharModalExcluir();
  });

  document.querySelectorAll('#dias-contraturno-grid input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', agendarSalvarContraturno);
  });
});

async function carregarAlunos() {
  mostrarEstado('loading');

  try {
    const res = await fetch(`/administrativo/alunos/${TURMA_ID}/json/`);
    if (!res.ok) throw new Error('Erro na requisição');
    const data = await res.json();

    todosAlunos = data.alunos || [];

    const sub = document.getElementById('subtitulo-turma');
    if (sub && data.turma) {
      const total = data.turma.total_alunos ?? todosAlunos.length;
      sub.textContent = `${total} aluno${total !== 1 ? 's' : ''} nesta turma.`;
    }

    mostrarEstado(null);
    aplicarFiltros();

  } catch (err) {
    console.error(err);
    mostrarEstado('erro');
  }
}

function agendarSalvarContraturno() {
  clearTimeout(timeoutContraturno);
  timeoutContraturno = setTimeout(salvarContraturno, 400);
}

async function salvarContraturno() {
  if (salvandoContraturno) return;

  const grid = document.getElementById('dias-contraturno-grid');
  const indicador = document.getElementById('contraturno-salvando');
  const dias = [...grid.querySelectorAll('input[type="checkbox"]:checked')].map(cb => Number(cb.value));

  salvandoContraturno = true;
  if (indicador) indicador.hidden = false;

  try {
    const res = await fetch(`/administrativo/alunos/${TURMA_ID}/contraturno/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({ dias_contraturno: dias }),
    });
    if (!res.ok) throw new Error();
    mostrarToast('Dias de contraturno atualizados.', 'success');
  } catch {
    mostrarToast('Erro ao salvar contraturno. Tente novamente.', 'error');
  } finally {
    salvandoContraturno = false;
    if (indicador) indicador.hidden = true;
  }
}

function abrirModalExcluir() {
  const total = TURMA_TOTAL_ALUNOS ?? todosAlunos.length;
  const desc = document.getElementById('modal-excluir-desc');
  const btnConfirmar = document.getElementById('btn-confirmar-excluir');

  if (total > 0) {
    desc.textContent = `A turma "${TURMA_NOME}" possui ${total} aluno${total !== 1 ? 's' : ''} vinculado${total !== 1 ? 's' : ''} e não pode ser excluída.`;
    btnConfirmar.disabled = true;
  } else {
    desc.textContent = `Deseja excluir a turma "${TURMA_NOME}"? Esta ação não pode ser desfeita.`;
    btnConfirmar.disabled = false;
  }
  document.getElementById('modal-excluir-overlay').hidden = false;
}

function fecharModalExcluir() {
  document.getElementById('modal-excluir-overlay').hidden = true;
}

function confirmarExcluirTurma() {
  const btn = document.getElementById('btn-confirmar-excluir');
  if (btn.disabled) return;
  document.getElementById('form-excluir-turma').submit();
}

function aplicarFiltros() {
  const busca        = document.getElementById('input-busca').value.toLowerCase().trim();
  const soBloqueados = document.getElementById('btn-somente-bloqueados').dataset.ativo === 'true';

  const filtrados = todosAlunos.filter(a => {
    const matchBusca = !busca ||
      a.nome_completo.toLowerCase().includes(busca) ||
      a.email.toLowerCase().includes(busca);
    const matchBloc = !soBloqueados || a.bloqueado;
    return matchBusca && matchBloc;
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
    const iniciais  = extrairIniciais(a.nome_completo);
    const cor       = CORES_AVATAR[somarChars(a.nome_completo) % CORES_AVATAR.length];
    const strikeCls = `strike-${Math.min(a.strikes_ativos, 2)}`;

    const expiracao = a.proximo_strike_expira_em
      ? `<span class="strike-expira">Expira ${formatarData(a.proximo_strike_expira_em)}</span>`
      : '';

    const statusHtml = renderStatus(a);

    const btnDesbl = a.bloqueado
      ? `<button class="btn-desbloquear"
           onclick="abrirModal('${escapar(a.id)}', '${escapar(a.nome_completo)}')">
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

function formatarData(iso) {
  return new Date(iso).toLocaleDateString('pt-BR');
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
