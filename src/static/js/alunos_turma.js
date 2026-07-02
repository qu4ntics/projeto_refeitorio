document.addEventListener('DOMContentLoaded', carregarTurmas);

async function carregarTurmas() {
  mostrarEstado('loading');

  try {
    const url = ARQUIVADAS
      ? '/administrativo/alunos/turmas/json/?arquivadas=1'
      : '/administrativo/alunos/turmas/json/';
    const res = await fetch(url);
    if (!res.ok) throw new Error('Erro na requisição');
    const data = await res.json();
    const turmas = data.turmas;

    if (!turmas || turmas.length === 0) {
      mostrarEstado('vazio');
      return;
    }

    mostrarEstado(null);
    renderizarCards(turmas);

  } catch (err) {
    console.error(err);
    mostrarEstado('erro');
  }
}

function renderizarCards(turmas) {
  const grid = document.getElementById('turmas-grid');
  grid.innerHTML = turmas.map(t => criarCardHTML(t)).join('');
  grid.hidden = false;
}

function criarCardHTML(t) {
  const temBloqueados = t.total_bloqueados > 0;
  const arquivada = ARQUIVADAS || t.ativo === false;

  const badgeBloqueados = temBloqueados
    ? `<span class="badge-bloqueados tem-bloqueados">
         <i class="fa-solid fa-lock"></i> ${t.total_bloqueados} bloqueado${t.total_bloqueados > 1 ? 's' : ''}
       </span>`
    : `<span class="badge-bloqueados zero">
         <i class="fa-solid fa-circle-check"></i> Sem bloqueios
       </span>`;

  const badgeArquivada = arquivada
    ? `<span class="badge-arquivada"><i class="fa-solid fa-box-archive"></i> Arquivada</span>`
    : '';

  const diasHTML = t.dias_contraturno && t.dias_contraturno.length > 0
    ? `<div class="turma-card-dias">
         ${t.dias_contraturno.map(d => `<span class="dia-chip">${escapar(d)}</span>`).join('')}
       </div>`
    : `<p class="turma-card-sem-dias">Sem contra-turno definido</p>`;

  const statBloqueadosClass = temBloqueados ? 'stat-item stat-danger' : 'stat-item';
  const statBloqueadosIcon  = temBloqueados ? 'fa-solid fa-lock' : 'fa-solid fa-lock-open';

  return `
    <a class="turma-card${arquivada ? ' turma-card-arquivada' : ''}" href="/administrativo/alunos/${t.id}/" title="Ver alunos de ${escapar(t.nome)}">
      <div class="turma-card-header">
        <div class="turma-card-icon">
          <i class="fa-solid fa-users-rectangle"></i>
        </div>
        <div class="turma-card-titulo">
          <span class="turma-card-nome">${escapar(t.nome)}</span>
          <span class="turma-card-turno">${escapar(t.turno_display || '—')}</span>
        </div>
        <div class="turma-card-badges">
          ${badgeArquivada}
          ${badgeBloqueados}
        </div>
      </div>

      ${diasHTML}

      <div class="turma-card-stats">
        <div class="stat-item">
          <i class="fa-solid fa-user-graduate"></i>
          <div>
            <span class="stat-value">${t.total_alunos}</span>
            <span class="stat-label">alunos</span>
          </div>
        </div>
        <div class="${statBloqueadosClass}">
          <i class="${statBloqueadosIcon}"></i>
          <div>
            <span class="stat-value">${t.total_bloqueados}</span>
            <span class="stat-label">bloqueado${t.total_bloqueados !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      <div class="turma-card-arrow">
        <i class="fa-solid fa-arrow-right"></i>
      </div>
    </a>
  `;
}

function mostrarEstado(tipo) {
  document.getElementById('estado-loading').hidden = tipo !== 'loading';
  document.getElementById('estado-vazio').hidden   = tipo !== 'vazio';
  document.getElementById('estado-erro').hidden    = tipo !== 'erro';
  const grid = document.getElementById('turmas-grid');
  if (tipo !== null) grid.hidden = true;
}

function escapar(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
