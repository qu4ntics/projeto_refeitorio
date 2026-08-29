(function () {
  'use strict';

  var SPINNER_HTML = '<span class="btn-spinner" aria-hidden="true"></span>';
  var DEFAULT_LOADING_TEXT = 'Processando...';

  var dialog = null;
  var dialogTitle = null;
  var dialogMessage = null;
  var dialogCancel = null;
  var dialogConfirm = null;
  var pendingForm = null;
  var lastFocused = null;

  function getDialogElements() {
    if (dialog) return;
    dialog = document.getElementById('confirm-dialog');
    if (!dialog) return;
    dialogTitle = dialog.querySelector('[data-confirm-title]');
    dialogMessage = dialog.querySelector('[data-confirm-message]');
    dialogCancel = dialog.querySelector('[data-confirm-cancel]');
    dialogConfirm = dialog.querySelector('[data-confirm-ok]');
  }

  function openDialog(title, message, confirmLabel) {
    getDialogElements();
    if (!dialog) return false;

    lastFocused = document.activeElement;
    if (dialogTitle) dialogTitle.textContent = title || 'Tem certeza?';
    if (dialogMessage) dialogMessage.textContent = message;
    if (dialogConfirm) dialogConfirm.textContent = confirmLabel || 'Confirmar';

    dialog.hidden = false;
    dialog.setAttribute('aria-hidden', 'false');
    document.body.classList.add('confirm-dialog-open');

    if (dialogConfirm) dialogConfirm.focus();
    return true;
  }

  function closeDialog() {
    getDialogElements();
    if (!dialog) return;

    if (pendingForm) {
      resetFormButtons(pendingForm);
    }

    dialog.hidden = true;
    dialog.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('confirm-dialog-open');
    pendingForm = null;

    if (dialogConfirm) {
      dialogConfirm.disabled = false;
      dialogConfirm.classList.remove('is-loading');
      dialogConfirm.removeAttribute('aria-busy');
      // O rótulo é reescrito a cada abertura, a partir do formulário.
      delete dialogConfirm.dataset.loadingOriginal;
    }
    if (dialogCancel) {
      dialogCancel.disabled = false;
    }

    if (lastFocused && typeof lastFocused.focus === 'function') {
      lastFocused.focus();
    }
  }

  function isButtonElement(el) {
    return el && (el.tagName === 'BUTTON' || el.tagName === 'INPUT');
  }

  function resetButtonLoading(btn) {
    if (!isButtonElement(btn) || !btn.classList.contains('is-loading')) return;

    if (btn.dataset.loadingOriginal) {
      if (btn.tagName === 'INPUT') {
        btn.value = btn.dataset.loadingOriginal;
      } else {
        btn.innerHTML = btn.dataset.loadingOriginal;
      }
      delete btn.dataset.loadingOriginal;
    }

    btn.disabled = false;
    btn.classList.remove('is-loading');
    btn.removeAttribute('aria-busy');
  }

  function resetFormButtons(form) {
    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(resetButtonLoading);
  }

  function setButtonLoading(btn, loadingText) {
    if (!isButtonElement(btn) || btn.classList.contains('is-loading')) return;

    if (btn.tagName === 'INPUT') {
      if (!btn.dataset.loadingOriginal) {
        btn.dataset.loadingOriginal = btn.value;
      }
      btn.value = loadingText;
    } else {
      if (!btn.dataset.loadingOriginal) {
        btn.dataset.loadingOriginal = btn.innerHTML;
      }
      btn.innerHTML = SPINNER_HTML + '<span class="btn-label">' + loadingText + '</span>';
    }

    btn.disabled = true;
    btn.classList.add('is-loading');
    btn.setAttribute('aria-busy', 'true');
  }

  function applyFormLoading(form, submitter) {
    var buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    buttons.forEach(function (btn) {
      if (submitter && btn !== submitter) return;
      var text = btn.getAttribute('data-loading-text') || DEFAULT_LOADING_TEXT;
      setButtonLoading(btn, text);
    });
  }

  /**
   * Um formulário pede confirmação declarando data-confirm-message. Título,
   * rótulo do botão e texto de carregamento saem dos data-* do próprio
   * formulário, para o diálogo servir a qualquer ação.
   */
  function exigeConfirmacao(form) {
    return form.hasAttribute('data-confirm-message');
  }

  function handleFormSubmit(event) {
    var form = event.target;
    if (form.tagName !== 'FORM') return;
    if ((form.getAttribute('method') || 'get').toLowerCase() !== 'post') return;
    if (form.hasAttribute('data-no-loading')) return;
    if (exigeConfirmacao(form) && form.dataset.confirmed !== 'true') return;

    var submitter = event.submitter || null;
    var confirmado = exigeConfirmacao(form) && form.dataset.confirmed === 'true';
    setTimeout(function () {
      applyFormLoading(form, submitter);
      if (confirmado) {
        form.removeAttribute('data-confirmed');
      }
    }, 0);
  }

  function handleConfirmSubmit(event) {
    var form = event.target;
    if (!exigeConfirmacao(form)) return;

    if (form.dataset.confirmed === 'true') {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    pendingForm = form;

    // Sem o diálogo no DOM, segue direto em vez de travar a ação.
    if (!openDialog(
      form.getAttribute('data-confirm-title'),
      form.getAttribute('data-confirm-message'),
      form.getAttribute('data-confirm-ok')
    )) {
      form.dataset.confirmed = 'true';
      form.requestSubmit();
    }
  }

  function initDialogHandlers() {
    getDialogElements();
    if (!dialog) return;

    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) {
        closeDialog();
      }
    });

    if (dialogCancel) {
      dialogCancel.addEventListener('click', closeDialog);
    }

    if (dialogConfirm) {
      dialogConfirm.addEventListener('click', function () {
        if (!pendingForm) {
          closeDialog();
          return;
        }

        var form = pendingForm;
        setButtonLoading(
          dialogConfirm,
          form.getAttribute('data-confirm-loading') || DEFAULT_LOADING_TEXT
        );
        if (dialogCancel) dialogCancel.disabled = true;

        closeDialog();
        form.dataset.confirmed = 'true';
        form.requestSubmit();
      });
    }

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && dialog && !dialog.hidden) {
        closeDialog();
      }
    });
  }

  document.addEventListener('submit', handleConfirmSubmit, true);
  document.addEventListener('submit', handleFormSubmit);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDialogHandlers);
  } else {
    initDialogHandlers();
  }
})();
