/**
 * Toasts no canto superior direito, usados em toda a aplicação.
 *
 * Também converte as mensagens do Django (framework messages) renderizadas no
 * base.html, para que um feedback vindo de redirect apareça igual a um vindo
 * de AJAX.
 */
(function () {
  'use strict';

  var ID_CONTAINER = 'toast-container';
  var DURACAO_MS = 4000;

  // Erro e aviso não somem sozinhos: costumam exigir uma ação de quem lê.
  var PERSISTENTES = ['error', 'warning'];

  var ICONES = {
    success: 'fa-circle-check',
    error: 'fa-circle-exclamation',
    warning: 'fa-triangle-exclamation',
    info: 'fa-circle-info',
  };

  function normalizarTipo(tipo) {
    if (tipo === 'danger') return 'error';
    if (tipo === 'debug') return 'info';
    return ICONES[tipo] ? tipo : 'info';
  }

  function getContainer() {
    var container = document.getElementById(ID_CONTAINER);
    if (container) return container;

    container = document.createElement('div');
    container.id = ID_CONTAINER;
    container.className = 'toast-container';
    // polite: anuncia sem interromper o que o leitor de tela está lendo.
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'false');
    document.body.appendChild(container);
    return container;
  }

  function fechar(toast) {
    if (toast.dataset.fechando === 'true') return;
    toast.dataset.fechando = 'true';
    toast.classList.add('hide');
    setTimeout(function () {
      toast.remove();
    }, 500);
  }

  function mostrarToast(mensagem, tipo) {
    if (!mensagem) return null;
    tipo = normalizarTipo(tipo);

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + tipo;
    toast.setAttribute('role', tipo === 'error' ? 'alert' : 'status');

    var icone = document.createElement('i');
    icone.className = 'fa-solid ' + ICONES[tipo];
    icone.setAttribute('aria-hidden', 'true');

    var texto = document.createElement('span');
    texto.className = 'toast__texto';
    // textContent (e não innerHTML): a mensagem pode conter dados do usuário.
    texto.textContent = mensagem;

    var fechaBtn = document.createElement('button');
    fechaBtn.type = 'button';
    fechaBtn.className = 'toast__fechar';
    fechaBtn.setAttribute('aria-label', 'Fechar aviso');
    fechaBtn.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';
    fechaBtn.addEventListener('click', function () {
      fechar(toast);
    });

    toast.appendChild(icone);
    toast.appendChild(texto);
    toast.appendChild(fechaBtn);
    getContainer().appendChild(toast);

    if (PERSISTENTES.indexOf(tipo) === -1) {
      setTimeout(function () {
        fechar(toast);
      }, DURACAO_MS);
    }

    return toast;
  }

  /**
   * Lê as mensagens que o base.html renderizou como dados e as transforma em
   * toasts. Ficam em markup em vez de JSON para não depender de escaping.
   */
  function converterMensagensDoDjango() {
    var pendentes = document.querySelectorAll('[data-toast-mensagem]');
    pendentes.forEach(function (el) {
      mostrarToast(el.textContent.trim(), el.getAttribute('data-toast-tipo'));
      el.remove();
    });
  }

  window.mostrarToast = mostrarToast;
  // Nome antigo, mantido para o script da lista de presença.
  window.showToast = mostrarToast;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', converterMensagensDoDjango);
  } else {
    converterMensagensDoDjango();
  }
})();
