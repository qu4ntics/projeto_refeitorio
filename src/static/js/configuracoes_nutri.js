document.addEventListener('DOMContentLoaded', function () {
  initConfigTabs();
  initRefeicoesForm();
  initCancelamentoExemplo();
});

function initConfigTabs() {
  const tabs = document.querySelectorAll('.config-tabs .week-tab[data-aba]');
  const paineis = document.querySelectorAll('.config-tab-panel');
  if (!tabs.length) return;

  const abaInicial = window.CONFIG_ABA_ATIVA || 'refeicoes';

  function ativarAba(aba, atualizarUrl) {
    tabs.forEach(function (tab) {
      const ativo = tab.dataset.aba === aba;
      tab.classList.toggle('active', ativo);
      tab.setAttribute('aria-selected', ativo ? 'true' : 'false');
    });
    paineis.forEach(function (painel) {
      const id = painel.id.replace('painel-', '');
      painel.classList.toggle('active', id === aba);
    });
    if (atualizarUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set('aba', aba);
      history.replaceState(null, '', url.pathname + url.search);
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      ativarAba(tab.dataset.aba, true);
    });
  });

  ativarAba(abaInicial, false);
}

function initCancelamentoExemplo() {
  const input = document.getElementById('id_minutos_cancelamento');
  const saida = document.getElementById('exemplo-horario-cancelamento');
  const minutosEl = document.getElementById('exemplo-minutos');
  const inicioEl = document.getElementById('exemplo-inicio-refeicao');
  if (!input || !saida) return;

  function horarioMenosMinutos(horarioStr, minutos) {
    const [h, m] = horarioStr.split(':').map(Number);
    let total = h * 60 + m - minutos;
    if (total < 0) total += 24 * 60;
    const horas = Math.floor(total / 60);
    const mins = total % 60;
    return String(horas).padStart(2, '0') + ':' + String(mins).padStart(2, '0');
  }

  function atualizar() {
    const minutos = parseInt(input.value, 10);
    if (Number.isNaN(minutos) || minutos < 0) return;

    const inicioRefeicao = (inicioEl && inicioEl.textContent.trim()) || '12:00';
    saida.textContent = horarioMenosMinutos(inicioRefeicao, minutos);
    if (minutosEl) minutosEl.textContent = String(minutos);
  }

  input.addEventListener('input', atualizar);
  atualizar();
}

function parseHorarioParaMinutos(horarioStr) {
  const [h, m] = horarioStr.split(':').map(Number);
  return h * 60 + m;
}

function minutosParaHorario(totalMinutos) {
  let normalizado = totalMinutos;
  while (normalizado < 0) normalizado += 24 * 60;
  normalizado %= 24 * 60;
  const horas = Math.floor(normalizado / 60);
  const mins = normalizado % 60;
  return String(horas).padStart(2, '0') + ':' + String(mins).padStart(2, '0');
}

function calcularLimitesPreReserva(aberturaStr, fechamentoStr, fechamentoPreStr) {
  const aberturaMin = parseHorarioParaMinutos(aberturaStr);
  const fechamentoMin = parseHorarioParaMinutos(fechamentoStr);
  const fechamentoPreMin = parseHorarioParaMinutos(fechamentoPreStr);

  const inicioMin = aberturaMin;
  const fimMin = fechamentoMin <= aberturaMin
    ? fechamentoMin + 24 * 60
    : fechamentoMin;

  const fimPreMin = fechamentoPreMin > aberturaMin
    ? fechamentoPreMin
    : fechamentoPreMin + 24 * 60;

  const maxFimPreMin = fimMin - 60;

  return {
    inicioMin,
    fimMin,
    fimPreMin,
    maxFimPreMin,
    diaFechamentoPre: fechamentoPreMin > aberturaMin ? 'dia anterior' : 'dia da refeição',
  };
}

function validarFechamentoPreReserva(aberturaStr, fechamentoStr, fechamentoPreStr) {
  if (!aberturaStr || !fechamentoStr || !fechamentoPreStr) {
    return 'Os horários de abertura, fechamento e fechamento da pré-reserva são obrigatórios.';
  }

  const limites = calcularLimitesPreReserva(aberturaStr, fechamentoStr, fechamentoPreStr);

  if (limites.fimPreMin <= limites.inicioMin) {
    return 'O fechamento da pré-reserva deve ser posterior à abertura da janela.';
  }
  if (limites.fimPreMin >= limites.fimMin) {
    return 'O fechamento da pré-reserva deve ser anterior ao fechamento da janela de reservas.';
  }
  if (limites.fimPreMin > limites.maxFimPreMin) {
    return 'O fechamento da pré-reserva deve ser pelo menos 1 hora antes do fechamento da janela geral.';
  }

  return '';
}

function initRefeicoesForm() {
  const form = document.getElementById('config-form');
  const boxes = document.querySelectorAll('.refeicao-config-box');
  if (!form || boxes.length === 0) return;

  function boxAtivo(box) {
    const toggle = box.querySelector('.toggle-ativo');
    return toggle && toggle.checked;
  }

  function atualizarEstadoBox(box) {
    const ativo = boxAtivo(box);
    box.classList.toggle('is-inativo', !ativo);
    box.querySelectorAll('[data-horarios] input').forEach(function (input) {
      input.disabled = !ativo;
    });
  }

  boxes.forEach(function (box) {
    const inputAbertura = box.querySelector('input[name^="abertura_"]');
    const inputFechamento = box.querySelector('input[name^="encerramento_"]');
    const inputFechamentoPre = box.querySelector('input[name^="fechamento_pre_reserva_"]');
    const txtAbertura = box.querySelector('.txt-abertura');
    const txtFechamento = box.querySelector('.txt-fechamento');
    const txtAberturaPre = box.querySelector('.txt-abertura-pre');
    const txtAberturaPreResumo = box.querySelector('.txt-abertura-pre-resumo');
    const txtFechamentoPre = box.querySelector('.txt-fechamento-pre');
    const txtFechamentoPreLimite = box.querySelector('.txt-fechamento-pre-limite');
    const txtDiaFechamentoPre = box.querySelector('.txt-dia-fechamento-pre');
    const toggle = box.querySelector('.toggle-ativo');

    function atualizarResumo() {
      if (inputAbertura && inputAbertura.value && txtAbertura) {
        txtAbertura.textContent = inputAbertura.value;
      }
      if (inputFechamento && inputFechamento.value && txtFechamento) {
        txtFechamento.textContent = inputFechamento.value;
      }
      if (inputAbertura && inputAbertura.value && txtAberturaPre) {
        txtAberturaPre.textContent = inputAbertura.value;
      }
      if (inputAbertura && inputAbertura.value && txtAberturaPreResumo) {
        txtAberturaPreResumo.textContent = inputAbertura.value;
      }
      if (inputFechamento && inputFechamento.value && txtFechamentoPreLimite) {
        txtFechamentoPreLimite.textContent = inputFechamento.value;
      }
      if (inputFechamentoPre && inputFechamentoPre.value && txtFechamentoPre) {
        txtFechamentoPre.textContent = inputFechamentoPre.value;
      }
      if (
        inputAbertura && inputFechamento && inputFechamentoPre
        && inputAbertura.value && inputFechamento.value && inputFechamentoPre.value
        && txtDiaFechamentoPre
      ) {
        const limites = calcularLimitesPreReserva(
          inputAbertura.value,
          inputFechamento.value,
          inputFechamentoPre.value
        );
        txtDiaFechamentoPre.textContent = limites.diaFechamentoPre;
      }
    }

    if (inputAbertura && inputFechamento) {
      inputAbertura.addEventListener('input', atualizarResumo);
      inputFechamento.addEventListener('input', atualizarResumo);
    }
    if (inputFechamentoPre) {
      inputFechamentoPre.addEventListener('input', atualizarResumo);
    }
    atualizarResumo();

    if (toggle) {
      toggle.addEventListener('change', function () {
        atualizarEstadoBox(box);
      });
    }

    atualizarEstadoBox(box);
  });

  form.addEventListener('submit', function (event) {
    let temErro = false;

    boxes.forEach(function (box) {
      if (!boxAtivo(box)) {
        box.classList.remove('has-error');
        const errorSpan = box.querySelector('.msg-erro-inline');
        if (errorSpan) errorSpan.textContent = '';
        return;
      }

      const inputAbertura = box.querySelector('input[name^="abertura_"]');
      const inputFechamento = box.querySelector('input[name^="encerramento_"]');
      const inputInicioConsumo = box.querySelector('input[name^="horario_consumo_"]');
      const inputFimConsumo = box.querySelector('input[name^="horario_fim_consumo_"]');
      const inputFechamentoPre = box.querySelector('input[name^="fechamento_pre_reserva_"]');
      const errorSpan = box.querySelector('.msg-erro-inline');

      box.classList.remove('has-error');
      if (errorSpan) errorSpan.textContent = '';

      if (!inputAbertura || !inputFechamento || !inputAbertura.value || !inputFechamento.value) {
        temErro = true;
        box.classList.add('has-error');
        if (errorSpan) errorSpan.textContent = 'Os horários de abertura e fechamento são obrigatórios.';
        return;
      }

      if (inputAbertura.value === inputFechamento.value) {
        temErro = true;
        box.classList.add('has-error');
        if (errorSpan) errorSpan.textContent = 'O horário de fechamento não pode ser idêntico ao de abertura.';
        return;
      }

      if (inputFechamentoPre) {
        const erroPre = validarFechamentoPreReserva(
          inputAbertura.value,
          inputFechamento.value,
          inputFechamentoPre.value
        );
        if (erroPre) {
          temErro = true;
          box.classList.add('has-error');
          if (errorSpan) errorSpan.textContent = erroPre;
          return;
        }
      }

      if (
        inputInicioConsumo && inputFimConsumo
        && inputInicioConsumo.value && inputFimConsumo.value
        && inputFimConsumo.value <= inputInicioConsumo.value
      ) {
        temErro = true;
        box.classList.add('has-error');
        if (errorSpan) errorSpan.textContent = 'O término da refeição deve ser posterior ao início.';
      }
    });

    if (temErro) {
      event.preventDefault();
      const primeiroErro = document.querySelector('.has-error');
      if (primeiroErro) {
        primeiroErro.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  });
}
