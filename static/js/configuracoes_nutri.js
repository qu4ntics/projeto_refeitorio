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
  if (!input || !saida) return;

  const encerramento = '09:30';

  function atualizar() {
    const minutos = parseInt(input.value, 10);
    if (Number.isNaN(minutos) || minutos < 0) return;

    const [h, m] = encerramento.split(':').map(Number);
    const total = h * 60 + m - minutos;
    const horas = Math.floor((total + 1440) % 1440 / 60);
    const mins = (total + 1440) % 60;
    const horario = String(horas).padStart(2, '0') + ':' + String(mins).padStart(2, '0');

    saida.textContent = horario;
    if (minutosEl) minutosEl.textContent = String(minutos);
  }

  input.addEventListener('input', atualizar);
  atualizar();
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
    box.querySelectorAll('[data-horarios] input[type="time"]').forEach(function (input) {
      input.disabled = !ativo;
    });
  }

  boxes.forEach(function (box) {
    const inputAbertura = box.querySelector('input[name^="abertura_"]');
    const inputFechamento = box.querySelector('input[name^="encerramento_"]');
    const txtAbertura = box.querySelector('.txt-abertura');
    const txtFechamento = box.querySelector('.txt-fechamento');
    const toggle = box.querySelector('.toggle-ativo');

    function atualizarResumo() {
      if (inputAbertura && inputAbertura.value && txtAbertura) {
        txtAbertura.textContent = inputAbertura.value;
      }
      if (inputFechamento && inputFechamento.value && txtFechamento) {
        txtFechamento.textContent = inputFechamento.value;
      }
    }

    if (inputAbertura && inputFechamento) {
      inputAbertura.addEventListener('input', atualizarResumo);
      inputFechamento.addEventListener('input', atualizarResumo);
      atualizarResumo();
    }

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
